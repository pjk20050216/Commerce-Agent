"""售后纠纷仲裁庭 Agent 测试。"""

from datetime import datetime, timedelta

import pytest

from src.agents.dispute_fact_restorer import FactRestorerAgent
from src.agents.dispute_negotiator import DISCLAIMER, NegotiatorAgent
from src.agents.dispute_rule_interpreter import RuleInterpreterAgent
from src.agents.dispute_rules import aggregate_responsibility, match_rules
from src.models.dispute import (
    ArbitrationVerdict,
    ChatMessageInput,
    DisputeClaim,
    DisputeOrderInput,
    DraftTone,
    LogisticsEventInput,
    MatchedRule,
    Responsibility,
    Speaker,
    UnboxingEvidence,
)


@pytest.fixture
def order() -> DisputeOrderInput:
    """三天前签收的订单。"""
    now = datetime.now()
    return DisputeOrderInput(
        order_id="ORD-2026-001",
        platform="淘宝",
        category="女装",
        amount=199.0,
        product_title="纯棉衬衫",
        paid_at=now - timedelta(days=5),
        shipped_at=now - timedelta(days=4),
        received_at=now - timedelta(days=3),
    )


@pytest.fixture
def chat_log() -> list[ChatMessageInput]:
    """消费者主张质量问题、商家拒绝退款的对话。"""
    now = datetime.now()
    return [
        ChatMessageInput(
            speaker=Speaker.CONSUMER,
            content="衣服洗了一次掉色严重，要求退货退款",
            sent_at=now - timedelta(days=2),
        ),
        ChatMessageInput(
            speaker=Speaker.MERCHANT,
            content="已经拆封使用过了，我们拒绝退款",
            sent_at=now - timedelta(days=2) + timedelta(hours=1),
        ),
    ]


@pytest.fixture
def logistics() -> list[LogisticsEventInput]:
    """已签收的物流轨迹。"""
    return [
        LogisticsEventInput(
            status="已签收",
            description="本人签收",
            occurred_at=datetime.now() - timedelta(days=3),
        )
    ]


@pytest.fixture
def unboxing() -> list[UnboxingEvidence]:
    """开箱实拍。"""
    return [
        UnboxingEvidence(
            image_url="https://example.invalid/1.jpg",
            description="领口掉色明显",
            captured_at=datetime.now() - timedelta(days=3),
        )
    ]


class TestDisputeRules:
    """规则库测试。"""

    def test_quality_rule_matched_by_facts(self) -> None:
        """事实条件满足即命中，不因措辞不同而漏判。"""
        facts = {"quality_issue": True, "beyond_quality_window": False}
        matched = match_rules(facts, "洗了一次就掉色")

        assert any(rule.rule_id == "R-QUALITY-01" for rule in matched)
        assert matched[0].weight >= matched[-1].weight

    def test_keyword_rule_matched_without_conditions(self) -> None:
        """无事实条件的规则（如辱骂）靠关键词触发。"""
        matched = match_rules({}, "客服辱骂我，态度恶劣")
        assert any(rule.rule_id == "R-ATTITUDE-01" for rule in matched)

    def test_excluded_category_favors_merchant(self) -> None:
        """定制商品不适用七日无理由。"""
        matched = match_rules({"excluded_category": True}, "")
        rule = next(item for item in matched if item.rule_id == "R-NOREASON-02")
        assert rule.favors is Responsibility.MERCHANT

    def test_aggregate_merchant_when_consumer_rules_dominate(self) -> None:
        """规则倾向消费者 → 责任判给商家。"""
        matched = [
            MatchedRule(
                rule_id="R-1",
                name="质量问题",
                category="质量",
                favors=Responsibility.CONSUMER,
                weight=0.9,
            ),
            MatchedRule(
                rule_id="R-2",
                name="拒绝退款",
                category="售后",
                favors=Responsibility.CONSUMER,
                weight=0.8,
            ),
        ]
        responsibility, confidence = aggregate_responsibility(matched)

        assert responsibility is Responsibility.MERCHANT
        assert confidence == 1.0

    def test_aggregate_shared_when_close(self) -> None:
        """双方权重接近时判为共担。"""
        matched = [
            MatchedRule(
                rule_id="R-1",
                name="消费者",
                category="质量",
                favors=Responsibility.CONSUMER,
                weight=0.8,
            ),
            MatchedRule(
                rule_id="R-2",
                name="商家",
                category="退货",
                favors=Responsibility.MERCHANT,
                weight=0.7,
            ),
        ]
        responsibility, _ = aggregate_responsibility(matched)
        assert responsibility is Responsibility.SHARED

    def test_aggregate_undetermined_without_rules(self) -> None:
        """无命中规则时责任不明。"""
        responsibility, confidence = aggregate_responsibility([])
        assert responsibility is Responsibility.UNDETERMINED
        assert confidence < 0.5


class TestFactRestorer:
    """事实还原测试。"""

    @pytest.mark.asyncio
    async def test_restore_builds_timeline_and_facts(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
        unboxing: list[UnboxingEvidence],
    ) -> None:
        """应还原时间线、关键事实与事实标记。"""
        restorer = FactRestorerAgent(enable_llm=False)
        sheet, facts = await restorer.restore(order, chat_log, logistics, unboxing, "")

        assert facts["received"] is True
        assert facts["quality_issue"] is True
        assert facts["opened"] is True
        assert facts["merchant_refused"] is True
        assert facts["within_seven_days"] is True
        # 已拆封 → 不再适用七日无理由
        assert facts["no_reason_window_ok"] is False

        assert sheet.timeline
        assert sheet.timeline[0].phase == "下单"
        assert any(node.phase == "签收" for node in sheet.timeline)
        assert sheet.evidence[0].type.value == "order"
        assert sheet.key_facts
        assert sheet.summary

    @pytest.mark.asyncio
    async def test_timeline_is_time_ordered(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
    ) -> None:
        """时间线按发生时间升序。"""
        restorer = FactRestorerAgent(enable_llm=False)
        sheet, _ = await restorer.restore(order, chat_log, logistics, [], "")

        stamps = [node.occurred_at for node in sheet.timeline if node.occurred_at]
        assert stamps == sorted(stamps)

    @pytest.mark.asyncio
    async def test_missing_evidence_reported_as_gaps(
        self, order: DisputeOrderInput, chat_log: list[ChatMessageInput]
    ) -> None:
        """主张质量问题但没有开箱影像时，应把缺口列出来。"""
        restorer = FactRestorerAgent(enable_llm=False)
        sheet, _ = await restorer.restore(order, chat_log, [], [], "")

        assert sheet.evidence_gaps
        assert any("开箱" in gap for gap in sheet.evidence_gaps)
        assert sheet.complete is False


class TestRuleInterpreter:
    """规则解读测试。"""

    @pytest.mark.asyncio
    async def test_verdict_assigns_merchant(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
        unboxing: list[UnboxingEvidence],
    ) -> None:
        """质量问题 + 商家拒绝退款 → 责任在商家。"""
        restorer = FactRestorerAgent(enable_llm=False)
        sheet, facts = await restorer.restore(order, chat_log, logistics, unboxing, "")

        interpreter = RuleInterpreterAgent(enable_llm=False)
        verdict = await interpreter.interpret("case-1", sheet, facts, "要求退货退款")

        assert verdict.responsibility is Responsibility.MERCHANT
        assert verdict.claim is DisputeClaim.REFUND_WITH_RETURN
        assert verdict.matched_rules
        assert verdict.legal_basis
        assert verdict.reasoning
        assert verdict.suggested_compensation
        assert verdict.deadline_advice

    @pytest.mark.asyncio
    async def test_legal_basis_deduplicated(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
        unboxing: list[UnboxingEvidence],
    ) -> None:
        """多条规则共用同一法条时不得重复引用。"""
        restorer = FactRestorerAgent(enable_llm=False)
        sheet, facts = await restorer.restore(order, chat_log, logistics, unboxing, "")

        interpreter = RuleInterpreterAgent(enable_llm=False)
        verdict = await interpreter.interpret("case-2", sheet, facts, "要求退货退款")

        assert len(verdict.legal_basis) == len(set(verdict.legal_basis))

    def test_claim_detection_priority(self) -> None:
        """诉求识别按优先级：赔偿优先于退货。"""
        assert (
            RuleInterpreterAgent._detect_claim("要求三倍赔偿", Responsibility.MERCHANT)
            is DisputeClaim.COMPENSATION
        )
        assert (
            RuleInterpreterAgent._detect_claim("申请退货退款", Responsibility.MERCHANT)
            is DisputeClaim.REFUND_WITH_RETURN
        )
        assert (
            RuleInterpreterAgent._detect_claim("随便", Responsibility.MERCHANT)
            is DisputeClaim.REFUND_WITH_RETURN
        )


class TestNegotiator:
    """话术生成测试。"""

    @pytest.mark.asyncio
    async def test_three_tones_generated(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
        unboxing: list[UnboxingEvidence],
    ) -> None:
        """默认生成投诉、申诉、协商三种话术。"""
        restorer = FactRestorerAgent(enable_llm=False)
        sheet, facts = await restorer.restore(order, chat_log, logistics, unboxing, "")
        interpreter = RuleInterpreterAgent(enable_llm=False)
        verdict = await interpreter.interpret("case-3", sheet, facts, "要求退货退款")

        agent = NegotiatorAgent(enable_llm=False)
        drafts = await agent.write_drafts(order, sheet, verdict)

        assert {draft.tone for draft in drafts} == {
            DraftTone.COMPLAINT,
            DraftTone.APPEAL,
            DraftTone.NEGOTIATION,
        }
        for draft in drafts:
            assert draft.title
            assert "事实经过" in draft.body
            assert "我的诉求" in draft.body
            assert draft.cited_clauses
            assert draft.next_actions
        assert DISCLAIMER

    @pytest.mark.asyncio
    async def test_single_tone_regeneration(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
        unboxing: list[UnboxingEvidence],
    ) -> None:
        """指定语气时只生成一条。"""
        restorer = FactRestorerAgent(enable_llm=False)
        sheet, facts = await restorer.restore(order, chat_log, logistics, unboxing, "")
        interpreter = RuleInterpreterAgent(enable_llm=False)
        verdict: ArbitrationVerdict = await interpreter.interpret(
            "case-4", sheet, facts, "要求退货退款"
        )

        agent = NegotiatorAgent(enable_llm=False)
        drafts = await agent.write_drafts(
            order, sheet, verdict, tones=[DraftTone.NEGOTIATION]
        )

        assert len(drafts) == 1
        assert drafts[0].tone is DraftTone.NEGOTIATION
