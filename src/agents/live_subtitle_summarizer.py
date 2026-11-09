"""
字幕摘要 Agent。

Description:
    从口播字幕中实时抽取「限量 500 件」「拍一发三」「前 100 名加赠」这类关键信息。

    刻意不调用 LLM：直播摘要是每秒都在跑的链路，模型延迟会让「实时」失效，
    因此这里用短语规则保证毫秒级出结果；需要更细的语义归纳时，
    由快照的 summary 字段在汇总阶段处理。
2026-11-09
"""

import logging
from typing import Any

from src.agents.base import AgentResult, AgentRole
from src.agents.consumer_base import ConsumerAgentBase
from src.agents.live_lexicon import detect_kinds, extract_prices, split_sentences
from src.graph.live_state import LiveState
from src.models.live import KeyPointKind, LiveKeyPoint, TranscriptSegment

logger = logging.getLogger(__name__)

# 各类型的置信度（价格最确定，承诺类需要人工确认）
KIND_CONFIDENCE: dict[KeyPointKind, float] = {
    KeyPointKind.PRICE: 0.8,
    KeyPointKind.LIMIT: 0.7,
    KeyPointKind.GIFT: 0.7,
    KeyPointKind.DEADLINE: 0.65,
    KeyPointKind.SPEC: 0.55,
    KeyPointKind.PROMISE: 0.5,
    KeyPointKind.OTHER: 0.4,
}

KIND_LABEL: dict[KeyPointKind, str] = {
    KeyPointKind.PRICE: "价格",
    KeyPointKind.LIMIT: "限量",
    KeyPointKind.GIFT: "赠品",
    KeyPointKind.DEADLINE: "时效",
    KeyPointKind.SPEC: "规格",
    KeyPointKind.PROMISE: "承诺",
    KeyPointKind.OTHER: "其他",
}

# 单条关键信息的文本上限
MAX_TEXT_CHARS = 60


class SubtitleSummarizerAgent(ConsumerAgentBase[LiveState]):
    """字幕摘要 Agent。

    Example:
        >>> agent = SubtitleSummarizerAgent(enable_llm=False)
        >>> points = agent.extract([segment])
        >>> points[0].kind
        <KeyPointKind.LIMIT: 'limit'>
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化字幕摘要 Agent。

        Args:
            enable_llm: 是否允许 LLM 增强（当前未使用，保留以统一构造参数）。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.LIVE_SUBTITLE_SUMMARIZER,
            enable_llm=enable_llm,
            **kwargs,
        )

    def extract(self, segments: list[TranscriptSegment]) -> list[LiveKeyPoint]:
        """从字幕中抽取关键信息。

        Args:
            segments: 字幕片段列表。

        Returns:
            去重后的关键信息列表（按出现顺序）。
        """
        points: list[LiveKeyPoint] = []
        seen: set[tuple[str, str]] = set()

        for segment in segments:
            for sentence in split_sentences(segment.text):
                for kind in detect_kinds(sentence):
                    if kind is KeyPointKind.PRICE:
                        for price in extract_prices(sentence):
                            text = f"报价 ¥{price:.0f}"
                            if not self._remember(seen, kind, text):
                                continue
                            points.append(
                                LiveKeyPoint(
                                    kind=kind,
                                    text=text,
                                    quote=sentence[:MAX_TEXT_CHARS],
                                    confidence=KIND_CONFIDENCE[kind],
                                    at_seconds=segment.start_seconds,
                                )
                            )
                        continue

                    text = sentence[:MAX_TEXT_CHARS]
                    if not self._remember(seen, kind, text):
                        continue
                    points.append(
                        LiveKeyPoint(
                            kind=kind,
                            text=text,
                            quote=sentence[:MAX_TEXT_CHARS],
                            confidence=KIND_CONFIDENCE.get(kind, 0.4),
                            at_seconds=segment.start_seconds,
                        )
                    )

        return points

    @staticmethod
    def _remember(seen: set[tuple[str, str]], kind: KeyPointKind, text: str) -> bool:
        """记录已产出的关键信息，避免同批重复。

        Args:
            seen: 已见集合。
            kind: 信息类型。
            text: 信息文本。

        Returns:
            True 表示首次出现可以产出，False 表示重复。
        """
        key = (kind.value, text)
        if key in seen:
            return False
        seen.add(key)
        return True

    async def execute(self, state: LiveState) -> AgentResult:
        """抽取关键信息（工作流节点接口）。

        Args:
            state: 直播状态。

        Returns:
            包含关键信息的结果对象。
        """
        try:
            points = self.extract(state.segments)
            state.key_points = points
            return AgentResult(
                success=True,
                data={"key_points": [point.model_dump(mode="json") for point in points]},
            )
        except Exception as exc:
            logger.exception("字幕摘要失败")
            return AgentResult(success=False, error=f"字幕摘要失败: {exc}")
