"""
直播购物分身工作流构建器。

Description:
    每批数据走一次增量流水线::

        START ─▶ SubtitleSummarizer ─┬─▶ DanmakuSentiment ─┐
                                     └─▶ PriceComparator ──┴─▶ Merge ─▶ END

    字幕是另外两路的输入（比价需要报价、情感与字幕互不依赖），
    因此字幕先跑，出结果后弹幕与比价并行。
2026-11-09
"""

import logging
from collections import Counter
from typing import Any

from langgraph.graph import END, StateGraph

from src.agents.live_danmaku_sentiment import (
    NEGATIVE_TAG_THRESHOLD,
    POSITIVE_TAG_THRESHOLD,
    DanmakuSentimentAgent,
)
from src.agents.live_price_comparator import PriceComparatorAgent
from src.agents.live_subtitle_summarizer import KIND_LABEL, SubtitleSummarizerAgent
from src.config.settings import Settings, get_settings
from src.graph.live_state import LiveState
from src.models.live import (
    DanmakuItem,
    LiveKeyPoint,
    LivePriceAlert,
    LiveSnapshot,
    PriceTrigger,
    SentimentBreakdown,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


class LiveWorkflow:
    """直播购物分身工作流。

    Attributes:
        app: 编译后的 LangGraph 应用。
    """

    def __init__(self, settings: Any | None = None, enable_llm: bool = True) -> None:
        """初始化工作流。

        Args:
            settings: 可选配置对象。
            enable_llm: 是否允许各 Agent 调用 LLM 增强。
        """
        self._settings = settings
        self._enable_llm = enable_llm
        self._builder = StateGraph(LiveState)
        self._build_graph()
        # 不挂 MemorySaver：状态由调用方完整传入并原样返回，
        # 挂 checkpointer 只会引入 msgpack 序列化 Pydantic 模型的告警，
        # 且复用 thread_id 时容易读到上一轮的陈旧状态。
        self.app = self._builder.compile()

    @property
    def settings(self) -> Settings:
        """获取配置（延迟初始化）。

        Returns:
            配置实例。
        """
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    def _build_graph(self) -> None:
        """构建状态图。"""
        self._builder.add_node("subtitle", self._subtitle_node)
        self._builder.add_node("danmaku", self._danmaku_node)
        self._builder.add_node("price", self._price_node)
        self._builder.add_node("merge", self._merge_node)

        self._builder.set_entry_point("subtitle")
        self._builder.add_edge("subtitle", "danmaku")
        self._builder.add_edge("subtitle", "price")
        self._builder.add_edge("danmaku", "merge")
        self._builder.add_edge("price", "merge")
        self._builder.add_edge("merge", END)

    def _agent_kwargs(self, state: LiveState) -> dict[str, Any]:
        """构造 Agent 公共参数。

        Args:
            state: 直播状态。

        Returns:
            关字参数。
        """
        return {
            "enable_llm": self._enable_llm,
            "settings": self._settings,
            "tenant_id": state.tenant_id or "system",
        }

    # ------------------------------------------------------------------
    # 节点
    # ------------------------------------------------------------------
    async def _subtitle_node(self, state: LiveState) -> dict[str, Any]:
        """字幕摘要节点。"""
        agent = SubtitleSummarizerAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {"error": result.error, "key_points": [], "current_step": "subtitle_failed"}
        return {
            "key_points": [LiveKeyPoint.model_validate(item) for item in result.data["key_points"]],
            "current_step": "subtitle_done",
        }

    async def _danmaku_node(self, state: LiveState) -> dict[str, Any]:
        """弹幕情感节点。"""
        agent = DanmakuSentimentAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {"error": result.error}
        return {"sentiment": SentimentBreakdown.model_validate(result.data["sentiment"])}

    async def _price_node(self, state: LiveState) -> dict[str, Any]:
        """比价节点。"""
        agent = PriceComparatorAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {"error": result.error}
        payload = result.data.get("price_alert")
        return {
            "price_alert": LivePriceAlert.model_validate(payload) if payload else None
        }

    async def _merge_node(self, state: LiveState) -> dict[str, Any]:
        """合并节点：把本批结果并入上一版快照。"""
        previous = state.snapshot
        points = self._merge_key_points(
            previous.key_points if previous else [], state.key_points
        )
        sentiment = self._merge_sentiment(
            previous.sentiment if previous else None, state.sentiment
        )
        price_alert = state.price_alert or (previous.price_alert if previous else None)

        snapshot = LiveSnapshot(
            session_id=state.session_id,
            room_id=state.room_id or (previous.room_id if previous else ""),
            title=state.title or (previous.title if previous else ""),
            status="running",
            key_points=points,
            sentiment=sentiment,
            price_alert=price_alert,
            processed_segments=(previous.processed_segments if previous else 0)
            + len(state.segments),
            processed_danmaku=(previous.processed_danmaku if previous else 0)
            + len(state.danmaku),
        )
        snapshot.summary = self._build_summary(snapshot)
        return {"result": snapshot, "current_step": "merged"}

    # ------------------------------------------------------------------
    # 合并逻辑
    # ------------------------------------------------------------------
    def _merge_key_points(
        self, existing: list[LiveKeyPoint], new_points: list[LiveKeyPoint]
    ) -> list[LiveKeyPoint]:
        """合并关键信息并去重。

        Args:
            existing: 已有关键信息。
            new_points: 本批新增。

        Returns:
            合并后的列表。
        """
        merged: list[LiveKeyPoint] = list(existing)
        index: dict[tuple[str, str], int] = {
            (point.kind.value, point.text): position
            for position, point in enumerate(merged)
        }

        for point in new_points:
            key = (point.kind.value, point.text)
            if key in index:
                # 同一信息重复播报：保留置信度更高的一次
                position = index[key]
                if point.confidence > merged[position].confidence:
                    merged[position] = point
                continue
            index[key] = len(merged)
            merged.append(point)

        cap = self.settings.live_max_key_points
        if len(merged) > cap:
            # 超出上限时保留最近的若干条（直播中最新报价最相关），
            # 但至少保留一条限量/赠品类信息，避免丢关键促销条件
            priority = [
                point
                for point in merged
                if point.kind.value in {"limit", "gift", "deadline"}
            ][:3]
            recent = merged[-cap:]
            for point in priority:
                if point not in recent:
                    recent.insert(0, point)
            merged = recent[-cap:]

        return merged

    def _merge_sentiment(
        self,
        previous: SentimentBreakdown | None,
        current: SentimentBreakdown | None,
    ) -> SentimentBreakdown:
        """合并弹幕情感统计。

        累计计数（便于看全场口碑），但热度与高频短语取最新窗口
        （便于看当下在聊什么）。

        Args:
            previous: 上一版统计。
            current: 本批统计。

        Returns:
            合并后的统计。
        """
        if current is None or current.total == 0:
            return previous or SentimentBreakdown()
        if previous is None or previous.total == 0:
            return current

        positive = previous.positive + current.positive
        negative = previous.negative + current.negative
        neutral = previous.neutral + current.neutral
        total = positive + negative + neutral
        score = round((positive - negative) / total, 3) if total else 0.0

        # 「口碑 X」标签跟着累计情感分走；其余标签（价格敏感、购买意向等）
        # 反映的是当下在聊什么，沿用最新窗口即可
        tags = [
            tag for tag in (current.tags or previous.tags) if not tag.startswith("口碑")
        ]
        if score >= POSITIVE_TAG_THRESHOLD:
            tags.insert(0, "口碑向好")
        elif score <= NEGATIVE_TAG_THRESHOLD:
            tags.insert(0, "口碑偏冷")
        else:
            tags.insert(0, "口碑中性")

        mood = "偏正面" if score > 0.1 else ("偏负面" if score < -0.1 else "较为中性")
        summary = (
            f"全场累计 {total} 条弹幕，情绪{mood}"
            f"（正向 {positive / total:.0%}、负向 {negative / total:.0%}），"
            f"当前口碑：{'、'.join(tags)}。"
        )

        return SentimentBreakdown(
            total=total,
            positive=positive,
            negative=negative,
            neutral=neutral,
            score=score,
            heat_per_minute=current.heat_per_minute,
            top_positive_phrases=current.top_positive_phrases or previous.top_positive_phrases,
            top_negative_phrases=current.top_negative_phrases or previous.top_negative_phrases,
            tags=tags,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # 摘要
    # ------------------------------------------------------------------
    def _build_summary(self, snapshot: LiveSnapshot) -> str:
        """生成全场摘要。

        Args:
            snapshot: 当前快照。

        Returns:
            摘要文本。
        """
        if not snapshot.key_points and snapshot.processed_segments == 0:
            return "尚未捕捉到有效口播信息。"

        counter = Counter(point.kind for point in snapshot.key_points)
        parts: list[str] = []
        if counter:
            detail = "、".join(
                f"{KIND_LABEL[kind]}{count}"
                for kind, count in counter.most_common()
                if kind in KIND_LABEL
            )
            parts.append(f"本场捕捉 {len(snapshot.key_points)} 条关键信息（{detail}）")

        if snapshot.price_alert:
            trigger: PriceTrigger = snapshot.price_alert.trigger
            parts.append(f"最近报价 ¥{trigger.price:.0f}：{snapshot.price_alert.advice}")

        if snapshot.sentiment.total:
            parts.append(snapshot.sentiment.summary)

        # 各段自身以句号结尾，拼接时去重，避免出现「。。」
        cleaned = [part.rstrip("。") for part in parts if part]
        return "；".join(cleaned) + "。" if cleaned else "尚未捕捉到有效口播信息。"

    # ------------------------------------------------------------------
    # 对外入口
    # ------------------------------------------------------------------
    async def process(
        self,
        session_id: str,
        segments: list[TranscriptSegment] | None = None,
        danmaku: list[DanmakuItem] | None = None,
        current_product: str | None = None,
        snapshot: LiveSnapshot | None = None,
        room_id: str | None = None,
        title: str | None = None,
        tenant_id: str = "",
    ) -> LiveSnapshot:
        """处理一批直播事件并返回新快照。

        Args:
            session_id: 会话标识。
            segments: 新增字幕。
            danmaku: 新增弹幕。
            current_product: 当前讲解商品。
            snapshot: 上一版快照。
            room_id: 直播间标识（首次创建时提供）。
            title: 直播标题（首次创建时提供）。
            tenant_id: 租户 ID。

        Returns:
            合并后的快照。
        """
        state = LiveState(
            session_id=session_id,
            room_id=room_id or (snapshot.room_id if snapshot else ""),
            title=title or (snapshot.title if snapshot else ""),
            tenant_id=tenant_id,
            snapshot=snapshot,
            segments=segments or [],
            danmaku=danmaku or [],
            current_product=current_product,
        )
        config = {"configurable": {"thread_id": f"live-{session_id}"}}
        result = await self.app.ainvoke(state, config=config)
        final = result if isinstance(result, LiveState) else LiveState.model_validate(result)
        if final.result is None:
            raise RuntimeError(final.error or "直播工作流未能生成快照")
        return final.result
