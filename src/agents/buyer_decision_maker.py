"""
决策官 Agent。

Description:
    把风格顾问、性价比分析师、质检员三路结论合成一张「买手决策卡」：
    加权评分 → 建议档位 → 推荐理由 → 风险预警 → 一句话行动建议。

    加权口径：综合分 = 风格匹配 × 风格权重 + 性价比 × 性价比权重 + 质量口碑 × 质量权重，
    再扣减风险惩罚（高风险、明显溢价、数据缺失）。
2026-11-09
"""

import logging
import uuid
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentResult, AgentRole
from src.agents.consumer_base import ConsumerAgentBase
from src.agents.price_analysis import value_score_from_comparison
from src.graph.buyer_state import BuyerState
from src.models.buyer import (
    AgentTraceItem,
    BuyerDecisionCard,
    CandidateProduct,
    DecisionWarning,
    PriceComparison,
    PriceVerdict,
    QualityAssessment,
    Recommendation,
    ReviewInsight,
    RiskLevel,
    StyleProfile,
    WeightedScore,
)

logger = logging.getLogger(__name__)

RECOMMENDATION_LABEL: dict[Recommendation, str] = {
    Recommendation.STRONG_BUY: "强烈推荐",
    Recommendation.BUY: "推荐购买",
    Recommendation.CONSIDER: "谨慎考虑",
    Recommendation.AVOID: "暂不推荐",
}

# 风险惩罚（从综合分中扣减）
RISK_PENALTY: dict[RiskLevel, float] = {
    RiskLevel.HIGH: 12.0,
    RiskLevel.MEDIUM: 4.0,
    RiskLevel.LOW: 0.0,
}
PENALTY_OVERPRICED = 5.0
PENALTY_WAIT = 2.0
PENALTY_MISSING_PRICE = 4.0


class DecisionMakerAgent(ConsumerAgentBase[BuyerState]):
    """决策官 Agent。

    Example:
        >>> maker = DecisionMakerAgent(enable_llm=False)
        >>> card = await maker.decide("u1", candidate, profile, 88.0, comparison, quality)
        >>> card.recommendation.value
        'buy'
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化决策官。

        Args:
            enable_llm: 是否允许 LLM 生成行动建议。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.BUYER_DECISION_MAKER,
            enable_llm=enable_llm,
            **kwargs,
        )
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """注册提示模板。"""
        self.register_prompt(
            "advice",
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是消费者身边那位「懂行的朋友」。根据给定的评分与结论，"
                        "用两句话给出行动建议：第一句说买不买，第二句说买之前必须确认什么。"
                        "不要重复罗列数据，不要编造信息，总字数不超过 90 字。",
                    ),
                    (
                        "human",
                        "商品：{title}\n"
                        "综合评分：{overall}\n"
                        "建议档位：{label}\n"
                        "风格匹配：{style}\n"
                        "性价比：{value}\n"
                        "质量口碑：{quality}\n"
                        "主要风险：{warnings}",
                    ),
                ]
            ),
        )

    # ------------------------------------------------------------------
    # 核心：合成决策卡
    # ------------------------------------------------------------------
    async def decide(
        self,
        user_id: str,
        candidate: CandidateProduct,
        profile: StyleProfile | None,
        style_fit: float | None,
        comparison: PriceComparison | None,
        quality: QualityAssessment | None,
    ) -> BuyerDecisionCard:
        """合成买手决策卡。

        Args:
            user_id: 用户 ID。
            candidate: 候选商品。
            profile: 风格画像，缺失时用空画像。
            style_fit: 风格匹配分，缺失时按中性 60。
            comparison: 比价结果，缺失时按「比价不可用」。
            quality: 质量评估，缺失时按中性分。

        Returns:
            买手决策卡。
        """
        profile = profile or StyleProfile(user_id=user_id)
        comparison = comparison or PriceComparison(
            query=candidate.title,
            current_price=candidate.price,
            source="unavailable",
            advice="本次未获得比价数据。",
        )
        quality = quality or QualityAssessment(
            score=60.0,
            risk_level=RiskLevel.MEDIUM,
            insight=ReviewInsight(summary="本次未获得质量数据。"),
            warnings=["本次未获得质量数据。"],
        )
        fit = 60.0 if style_fit is None else style_fit

        weights = self.settings.buyer_score_weights
        value_score = self._value_score(comparison)
        overall = (
            fit * weights["style"]
            + value_score * weights["value"]
            + quality.score * weights["quality"]
        )

        overall = self._apply_penalties(overall, comparison, quality)
        overall = round(max(0.0, min(100.0, overall)), 2)

        recommendation = self._recommendation(overall)
        score = WeightedScore(
            style_fit=round(fit, 2),
            value_score=round(value_score, 2),
            quality_score=round(quality.score, 2),
            weights=weights,
            overall=overall,
        )

        reasons = self._build_reasons(profile, fit, comparison, quality)
        warnings = self._build_warnings(candidate, profile, fit, comparison, quality)
        advice = self._fallback_advice(recommendation, comparison, quality, warnings)

        polished = await self.try_generate(
            self.get_prompt("advice"),
            {
                "title": candidate.title,
                "overall": f"{overall:.0f}",
                "label": RECOMMENDATION_LABEL[recommendation],
                "style": f"{fit:.0f}",
                "value": f"{value_score:.0f}",
                "quality": f"{quality.score:.0f}",
                "warnings": "；".join(item.message for item in warnings[:3]) or "无明显风险",
            },
            accept=lambda text: 10 <= len(text) <= 220,
        )
        if polished:
            advice = polished

        return BuyerDecisionCard(
            card_id=f"card_{uuid.uuid4().hex[:12]}",
            user_id=profile.user_id or user_id,
            candidate=candidate,
            style_profile=profile,
            price_comparison=comparison,
            quality=quality,
            score=score,
            recommendation=recommendation,
            reasons=reasons,
            warnings=warnings,
            buy_advice=advice,
            is_mock_data=comparison.is_mock,
            agent_trace=[],
        )

    # ------------------------------------------------------------------
    # 打分
    # ------------------------------------------------------------------
    @staticmethod
    def _value_score(comparison: PriceComparison) -> float:
        """计算性价比得分。

        Args:
            comparison: 比价结果。

        Returns:
            性价比得分；比价不可用时给中性偏保守的 65 分。
        """
        if comparison.source == "unavailable":
            return 65.0
        return value_score_from_comparison(comparison)

    def _apply_penalties(
        self,
        overall: float,
        comparison: PriceComparison,
        quality: QualityAssessment,
    ) -> float:
        """扣减风险惩罚。

        Args:
            overall: 扣减前的加权分。
            comparison: 比价结果。
            quality: 质量评估。

        Returns:
            扣减后的分数。
        """
        if quality.risk_level is not RiskLevel.LOW:
            overall -= RISK_PENALTY[quality.risk_level]
        if comparison.verdict is PriceVerdict.OVERPRICED:
            overall -= PENALTY_OVERPRICED
        elif comparison.verdict is PriceVerdict.WAIT:
            overall -= PENALTY_WAIT
        if comparison.source == "unavailable":
            overall -= PENALTY_MISSING_PRICE
        return overall

    def _recommendation(self, overall: float) -> Recommendation:
        """按阈值输出建议档位。

        Args:
            overall: 综合评分。

        Returns:
            建议档位。
        """
        settings = self.settings
        if overall >= settings.buyer_strong_buy_threshold:
            return Recommendation.STRONG_BUY
        if overall >= settings.buyer_buy_threshold:
            return Recommendation.BUY
        if overall >= settings.buyer_consider_threshold:
            return Recommendation.CONSIDER
        return Recommendation.AVOID

    # ------------------------------------------------------------------
    # 理由与预警
    # ------------------------------------------------------------------
    def _build_reasons(
        self,
        profile: StyleProfile,
        fit: float,
        comparison: PriceComparison,
        quality: QualityAssessment,
    ) -> list[str]:
        """构造推荐理由。

        Args:
            profile: 风格画像。
            fit: 风格匹配分。
            comparison: 比价结果。
            quality: 质量评估。

        Returns:
            理由列表。
        """
        reasons: list[str] = []

        if profile.dominant_styles:
            top = profile.dominant_styles[0]
            reasons.append(f"风格匹配 {fit:.0f} 分，偏好「{top.name}」权重 {top.weight:.0%}")
        else:
            reasons.append(f"风格匹配 {fit:.0f} 分（行为样本不足，按中性处理）")

        if comparison.source == "unavailable":
            reasons.append("未取得全网比价数据，价格维度未计入")
        elif comparison.verdict is PriceVerdict.GREAT_DEAL:
            reasons.append(
                f"价格处于近期低位：当前 ¥{comparison.current_price:.0f}，"
                f"历史最低 ¥{comparison.historical_low:.0f}"
                if comparison.historical_low
                else f"价格接近全网最低 ¥{comparison.lowest.price:.0f}"
            )
        elif comparison.verdict is PriceVerdict.FAIR:
            reasons.append(f"价格合理：{comparison.advice}")
        else:
            reasons.append(f"价格偏高：{comparison.advice}")

        if quality.insight.total_reviews:
            reasons.append(
                f"质量口碑 {quality.score:.0f} 分，"
                f"样本 {quality.insight.total_reviews} 条，"
                f"差评占比 {quality.insight.negative_ratio:.0%}"
            )
        else:
            reasons.append("缺少评价样本，质量维度参考价值有限")

        return reasons

    def _build_warnings(
        self,
        candidate: CandidateProduct,
        profile: StyleProfile,
        fit: float,
        comparison: PriceComparison,
        quality: QualityAssessment,
    ) -> list[DecisionWarning]:
        """构造风险预警。

        Args:
            candidate: 候选商品。
            profile: 风格画像。
            fit: 风格匹配分。
            comparison: 比价结果。
            quality: 质量评估。

        Returns:
            预警列表。
        """
        warnings: list[DecisionWarning] = []

        # 数据可信度预警必须排在最前面，避免用户把模拟数据当成真实行情
        if comparison.is_mock:
            warnings.append(
                DecisionWarning(
                    kind="data",
                    severity=RiskLevel.HIGH,
                    message=(
                        f"比价数据来自模拟数据源（{comparison.source}），仅用于演示价格结论，"
                        "不代表真实行情。"
                    ),
                    evidence="配置 ELASTICSEARCH_URL 或 PRICE_CRAWLER_ENDPOINT 后可获得真实报价。",
                )
            )
        elif comparison.source == "unavailable":
            warnings.append(
                DecisionWarning(
                    kind="data",
                    severity=RiskLevel.MEDIUM,
                    message="比价数据源不可用，本卡未包含全网价格对比。",
                )
            )

        if comparison.verdict is PriceVerdict.OVERPRICED and comparison.vs_lowest_pct is not None:
            warnings.append(
                DecisionWarning(
                    kind="price",
                    severity=RiskLevel.MEDIUM,
                    message=(
                        f"当前价 ¥{comparison.current_price:.0f} 比全网最低价高 "
                        f"{comparison.vs_lowest_pct * 100:.0f}%。"
                    ),
                    evidence=comparison.advice,
                )
            )

        for text in quality.warnings:
            warnings.append(
                DecisionWarning(
                    kind="quality",
                    severity=quality.risk_level,
                    message=text,
                    evidence=quality.insight.evidence_quotes[0]
                    if quality.insight.evidence_quotes
                    else None,
                )
            )

        if profile.dominant_styles and fit < 60:
            warnings.append(
                DecisionWarning(
                    kind="style",
                    severity=RiskLevel.MEDIUM,
                    message=(
                        f"与你的常用风格匹配度偏低（{fit:.0f} 分），"
                        f"你常买的风格是「{profile.dominant_styles[0].name}」。"
                    ),
                )
            )

        band = profile.price_band
        if band.max_price is not None and candidate.price > band.max_price * 1.5:
            warnings.append(
                DecisionWarning(
                    kind="price",
                    severity=RiskLevel.LOW,
                    message=(
                        f"价格 ¥{candidate.price:.0f} 超过你的常用价格带上沿 "
                        f"¥{band.max_price:.0f} 的 1.5 倍。"
                    ),
                )
            )

        return warnings

    def _fallback_advice(
        self,
        recommendation: Recommendation,
        comparison: PriceComparison,
        quality: QualityAssessment,
        warnings: list[DecisionWarning],
    ) -> str:
        """生成规则版行动建议。

        Args:
            recommendation: 建议档位。
            comparison: 比价结果。
            quality: 质量评估。
            warnings: 预警列表。

        Returns:
            行动建议文本。
        """
        label = RECOMMENDATION_LABEL[recommendation]
        price_part = comparison.advice or "价格数据缺失。"
        if quality.risk_level is RiskLevel.HIGH:
            quality_part = "质量风险偏高，下单前务必确认退换政策。"
        elif quality.insight.defect_keywords:
            top = quality.insight.defect_keywords[0]
            quality_part = f"重点留意「{top.keyword}」问题，收货后第一时间验货。"
        else:
            quality_part = "暂无明显质量集中问题。"

        prefix = f"{label}。"
        if recommendation is Recommendation.AVOID:
            prefix = "暂不推荐。"
        return f"{prefix}{price_part}{quality_part}"

    async def execute(self, state: BuyerState) -> AgentResult:
        """合成决策卡（工作流节点接口）。

        Args:
            state: 买手团状态。

        Returns:
            包含决策卡的结果对象。
        """
        try:
            card = await self.decide(
                user_id=state.user_id,
                candidate=state.candidate,
                profile=state.style_profile,
                style_fit=state.style_fit,
                comparison=state.price_comparison,
                quality=state.quality,
            )
            card.agent_trace = list(state.agent_trace) + [
                AgentTraceItem(
                    agent=self.role.value,
                    status="completed",
                    detail=(
                        f"综合 {card.score.overall:.0f} 分 → "
                        f"{RECOMMENDATION_LABEL[card.recommendation]}，"
                        f"{len(card.warnings)} 条预警"
                    ),
                )
            ]
            state.card = card
            return AgentResult(
                success=True,
                data={"card": card.model_dump(mode="json")},
            )
        except Exception as exc:
            logger.exception("决策官执行失败")
            return AgentResult(success=False, error=f"决策卡合成失败: {exc}")
