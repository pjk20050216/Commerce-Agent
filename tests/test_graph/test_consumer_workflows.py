"""消费者侧三套工作流测试。"""

from datetime import datetime, timedelta

import pytest

from src.clients.price_search import reset_price_search_backend
from src.graph.buyer_workflow import BuyerTeamWorkflow
from src.graph.dispute_workflow import DisputeTribunalWorkflow
from src.graph.live_workflow import LiveWorkflow
from src.models.buyer import BrowsingAction, BrowsingRecord, CandidateProduct, Recommendation
from src.models.dispute import (
    ChatMessageInput,
    DisputeOrderInput,
    DraftTone,
    LogisticsEventInput,
    Responsibility,
    Speaker,
    UnboxingEvidence,
)
from src.models.live import DanmakuItem, KeyPointKind, TranscriptSegment


@pytest.fixture(autouse=True)
def _reset_backend() -> None:
    """清理比价数据源单例。"""
    reset_price_search_backend()
    yield
    reset_price_search_backend()


class TestBuyerTeamWorkflow:
    """虚拟买手团工作流。"""

    @pytest.mark.asyncio
    async def test_run_produces_card_with_trace(self) -> None:
        """三路 Agent 并行后应产出决策卡并留下执行痕迹。"""
        workflow = BuyerTeamWorkflow(enable_llm=False)
        card = await workflow.run_card(
            user_id="u1",
            candidate=CandidateProduct(
                title="极简风纯色棉质衬衫",
                price=199.0,
                category="女装",
                tags=["极简", "纯色"],
                reviews=["掉色严重", "尺码偏小"],
                return_rate=0.23,
            ),
            history=[
                BrowsingRecord(
                    item_id="1",
                    title="简约纯色T恤",
                    category="女装",
                    tags=["极简", "纯色"],
                    price=89.0,
                    action=BrowsingAction.PURCHASE,
                )
            ],
            tenant_id="dev",
        )

        assert card.user_id == "u1"
        assert card.score.overall > 0
        assert card.recommendation in set(Recommendation)
        assert card.style_profile.dominant_styles
        assert card.price_comparison.quotes
        assert card.quality.insight.defect_keywords

        agents = {item.agent for item in card.agent_trace}
        assert agents == {
            "buyer_style_advisor",
            "buyer_value_analyst",
            "buyer_quality_inspector",
            "buyer_decision_maker",
        }

    @pytest.mark.asyncio
    async def test_run_returns_state_with_card(self) -> None:
        """run() 返回完整状态，便于调用方读取中间产物。"""
        workflow = BuyerTeamWorkflow(enable_llm=False)
        state = await workflow.run(
            "u2",
            CandidateProduct(title="纯棉T恤", price=89.0, reviews=["质量很好"]),
        )

        assert state.card is not None
        assert state.current_step == "decided"
        assert state.style_profile is not None
        assert state.price_comparison is not None
        assert state.quality is not None


class TestDisputeTribunalWorkflow:
    """纠纷仲裁工作流。"""

    @pytest.mark.asyncio
    async def test_run_case_end_to_end(self) -> None:
        """事实 → 规则 → 话术三段应串起来。"""
        now = datetime.now()
        order = DisputeOrderInput(
            order_id="ORD-W-1",
            platform="淘宝",
            amount=199.0,
            product_title="纯棉衬衫",
            received_at=now - timedelta(days=3),
        )

        workflow = DisputeTribunalWorkflow(enable_llm=False)
        result = await workflow.run_case(
            order=order,
            chat_log=[
                ChatMessageInput(
                    speaker=Speaker.CONSUMER,
                    content="掉色严重，要求退货退款",
                    sent_at=now - timedelta(days=2),
                ),
                ChatMessageInput(
                    speaker=Speaker.MERCHANT,
                    content="拆封了，拒绝退款",
                    sent_at=now - timedelta(days=2),
                ),
            ],
            logistics=[
                LogisticsEventInput(status="已签收", occurred_at=now - timedelta(days=3))
            ],
            unboxing=[
                UnboxingEvidence(
                    image_url="https://example.invalid/a.jpg",
                    description="领口掉色",
                )
            ],
            claim_text="要求退货退款",
            tenant_id="dev",
        )

        assert result.case_id
        assert result.order_id == "ORD-W-1"
        assert result.verdict.responsibility is Responsibility.MERCHANT
        assert result.verdict.matched_rules
        assert result.fact_sheet.timeline
        assert len(result.drafts) == 3
        assert {draft.tone for draft in result.drafts} == {
            DraftTone.COMPLAINT,
            DraftTone.APPEAL,
            DraftTone.NEGOTIATION,
        }
        assert "不构成法律意见" in result.disclaimer


class TestLiveWorkflow:
    """直播购物分身工作流。"""

    @pytest.mark.asyncio
    async def test_process_batch_extracts_and_compares(self) -> None:
        """一批数据应产出关键信息、弹幕口碑与比价提醒。"""
        workflow = LiveWorkflow(enable_llm=False)
        snapshot = await workflow.process(
            session_id="s1",
            segments=[
                TranscriptSegment(
                    start_seconds=0,
                    end_seconds=10,
                    text="限量500件，拍一发三，到手价199",
                )
            ],
            danmaku=[DanmakuItem(text="冲了"), DanmakuItem(text="太贵")],
            current_product="纯棉衬衫",
            room_id="room1",
            title="衬衫专场",
        )

        assert snapshot.session_id == "s1"
        assert snapshot.room_id == "room1"
        assert snapshot.key_points
        assert snapshot.price_alert is not None
        assert snapshot.price_alert.trigger.price == 199.0
        assert snapshot.sentiment.total == 2
        assert snapshot.processed_segments == 1
        assert snapshot.processed_danmaku == 2
        assert snapshot.summary

    @pytest.mark.asyncio
    async def test_incremental_merge_accumulates(self) -> None:
        """第二批数据应在上一次快照基础上累加，而不是覆盖。"""
        workflow = LiveWorkflow(enable_llm=False)
        first = await workflow.process(
            session_id="s2",
            segments=[
                TranscriptSegment(start_seconds=0, end_seconds=5, text="限量500件")
            ],
            danmaku=[DanmakuItem(text="冲了")],
            room_id="room2",
        )
        second = await workflow.process(
            session_id="s2",
            segments=[
                TranscriptSegment(start_seconds=5, end_seconds=9, text="倒计时3分钟")
            ],
            danmaku=[DanmakuItem(text="划算")],
            snapshot=first,
        )

        assert second.processed_segments == 2
        assert second.processed_danmaku == 2
        assert len(second.key_points) == 2
        assert second.sentiment.total == 2
        assert second.room_id == "room2"

    @pytest.mark.asyncio
    async def test_duplicate_key_point_not_doubled(self) -> None:
        """同一条信息重复播报不应产生重复条目。"""
        workflow = LiveWorkflow(enable_llm=False)
        first = await workflow.process(
            session_id="s3",
            segments=[
                TranscriptSegment(start_seconds=0, end_seconds=5, text="限量500件")
            ],
        )
        second = await workflow.process(
            session_id="s3",
            segments=[
                TranscriptSegment(start_seconds=20, end_seconds=25, text="限量500件")
            ],
            snapshot=first,
        )

        assert len(second.key_points) == 1
        assert second.key_points[0].kind is KeyPointKind.LIMIT

    @pytest.mark.asyncio
    async def test_empty_batch_keeps_previous_snapshot(self) -> None:
        """空批次不应清空已有快照内容。"""
        workflow = LiveWorkflow(enable_llm=False)
        first = await workflow.process(
            session_id="s4",
            segments=[
                TranscriptSegment(start_seconds=0, end_seconds=5, text="假一赔十")
            ],
            danmaku=[DanmakuItem(text="支持")],
        )
        second = await workflow.process(session_id="s4", snapshot=first)

        assert len(second.key_points) == 1
        assert second.sentiment.total == 1
        assert second.processed_segments == 1
