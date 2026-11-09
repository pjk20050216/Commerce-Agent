"""
弹幕情感 Agent。

Description:
    统计一段时间窗口内的弹幕情感分布与热度，给出「大众口碑标签」。
    典型输出：正向 62%、负向 18%，高频正向词「冲」「划算」，
    高频负向词「太贵」，标签「购买意向强」「价格敏感」。

    为什么用词典而不是模型：弹幕量大（每秒几十条）、单条极短（3-10 字），
    模型调用既慢又不稳定；词典 + 频次统计在这个场景更可靠。
2026-11-09
"""

import logging
from collections import Counter
from typing import Any

from src.agents.base import AgentResult, AgentRole
from src.agents.consumer_base import ConsumerAgentBase
from src.agents.live_lexicon import (
    NEGATIVE_PHRASES,
    POSITIVE_PHRASES,
    classify_danmaku,
    matched_phrases,
)
from src.graph.live_state import LiveState
from src.models.live import DanmakuItem, SentimentBreakdown

logger = logging.getLogger(__name__)

# 热度分层（每分钟弹幕数）
HEAT_HIGH = 20.0
HEAT_LOW = 5.0

# 情感标签阈值：正向弹幕数达到负向的 1.5 倍左右（score≈0.2）即认为口碑向好
POSITIVE_TAG_THRESHOLD = 0.2
NEGATIVE_TAG_THRESHOLD = -0.2


class DanmakuSentimentAgent(ConsumerAgentBase[LiveState]):
    """弹幕情感 Agent。

    Example:
        >>> agent = DanmakuSentimentAgent(enable_llm=False)
        >>> result = agent.analyze([DanmakuItem(text="太贵了")], 60)
        >>> result.tags
        ['价格敏感', '口碑偏冷']
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化弹幕情感 Agent。

        Args:
            enable_llm: 是否允许 LLM 增强（当前未使用，保留以统一构造参数）。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.LIVE_DANMAKU_SENTIMENT,
            enable_llm=enable_llm,
            **kwargs,
        )

    def analyze(
        self,
        danmaku: list[DanmakuItem],
        window_seconds: int | None = None,
    ) -> SentimentBreakdown:
        """分析弹幕情感。

        Args:
            danmaku: 弹幕列表。
            window_seconds: 统计窗口秒数，缺省取配置值。

        Returns:
            情感分析结果。
        """
        window = window_seconds or self.settings.live_danmaku_window_seconds
        total = len(danmaku)
        if total == 0:
            return SentimentBreakdown(summary="本窗口没有弹幕，暂无口碑参考。")

        positive = negative = neutral = 0
        positive_counter: Counter[str] = Counter()
        negative_counter: Counter[str] = Counter()

        for item in danmaku:
            label = classify_danmaku(item.text)
            if label == "positive":
                positive += 1
                positive_counter.update(matched_phrases(item.text, POSITIVE_PHRASES))
            elif label == "negative":
                negative += 1
                negative_counter.update(matched_phrases(item.text, NEGATIVE_PHRASES))
            else:
                neutral += 1

        score = round((positive - negative) / total, 3)
        heat = round(total / (window / 60.0), 2) if window > 0 else 0.0
        tags = self._tags(score, heat, positive_counter, negative_counter)

        return SentimentBreakdown(
            total=total,
            positive=positive,
            negative=negative,
            neutral=neutral,
            score=score,
            heat_per_minute=heat,
            top_positive_phrases=[item for item, _ in positive_counter.most_common(3)],
            top_negative_phrases=[item for item, _ in negative_counter.most_common(3)],
            tags=tags,
            summary=self._summary(total, positive, negative, score, tags),
        )

    @staticmethod
    def _tags(
        score: float,
        heat: float,
        positive_counter: Counter[str],
        negative_counter: Counter[str],
    ) -> list[str]:
        """生成口碑标签。

        Args:
            score: 情感得分。
            heat: 每分钟弹幕数。
            positive_counter: 正向词频次。
            negative_counter: 负向词频次。

        Returns:
            标签列表。
        """
        tags: list[str] = []

        if score >= POSITIVE_TAG_THRESHOLD:
            tags.append("口碑向好")
        elif score <= NEGATIVE_TAG_THRESHOLD:
            tags.append("口碑偏冷")
        else:
            tags.append("口碑中性")

        if any(word in negative_counter for word in ("太贵", "贵了", "不值", "划不来")):
            tags.append("价格敏感")
        if any(word in positive_counter for word in ("冲", "买它", "已拍", "下单", "抢到")):
            tags.append("购买意向强")
        if heat >= HEAT_HIGH:
            tags.append("热度高")
        elif heat <= HEAT_LOW:
            tags.append("热度偏低")

        return tags

    @staticmethod
    def _summary(
        total: int, positive: int, negative: int, score: float, tags: list[str]
    ) -> str:
        """生成一句话结论。

        Args:
            total: 弹幕总数。
            positive: 正向数。
            negative: 负向数。
            score: 情感得分。
            tags: 标签。

        Returns:
            结论文本。
        """
        positive_ratio = positive / total if total else 0
        negative_ratio = negative / total if total else 0
        mood = "偏正面" if score > 0.1 else ("偏负面" if score < -0.1 else "较为中性")
        return (
            f"近 {total} 条弹幕情绪{mood}（正向 {positive_ratio:.0%}、负向 {negative_ratio:.0%}），"
            f"标签：{'、'.join(tags)}。"
        )

    async def execute(self, state: LiveState) -> AgentResult:
        """分析弹幕（工作流节点接口）。

        Args:
            state: 直播状态。

        Returns:
            包含情感分析结果的对象。
        """
        try:
            sentiment = self.analyze(state.danmaku)
            state.sentiment = sentiment
            return AgentResult(
                success=True,
                data={"sentiment": sentiment.model_dump(mode="json")},
            )
        except Exception as exc:
            logger.exception("弹幕情感分析失败")
            return AgentResult(success=False, error=f"弹幕情感分析失败: {exc}")
