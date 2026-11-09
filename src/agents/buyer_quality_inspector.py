"""
质检员 Agent。

Description:
    读取商品评价与退货率，挖出反复出现的缺陷关键词，给出风险等级。
    典型输出：「掉色」出现 12 次（材质类，严重度 0.8），退货率 23% 高于类目基准 8%。

    设计取舍：只对传入的评价样本做统计，不猜测平台未提供的全量数据；
    退货率缺失时不臆造数值，只在结论里标注「无退货率数据」。
2026-11-09
"""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentResult, AgentRole
from src.agents.buyer_review_lexicon import (
    CATEGORY_PENALTY,
    baseline_return_rate,
    extract_defects,
    has_defect,
    is_negative_review,
)
from src.agents.consumer_base import ConsumerAgentBase
from src.graph.buyer_state import BuyerState
from src.models.buyer import (
    AgentTraceItem,
    CandidateProduct,
    QualityAssessment,
    ReviewInsight,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# 各扣分项上限
MAX_NEGATIVE_PENALTY = 40.0
MAX_DEFECT_PENALTY = 40.0
MAX_RETURN_PENALTY = 25.0

# 无评价样本时的中性质量分
NEUTRAL_SCORE = 70.0

# 差评占比的先验（贝叶斯平滑）：
# 4 条评价里有 3 条差评时原始占比 75%，但样本太小，
# 用 0.15 的先验与强度 4 平滑后约 45%，避免小样本直接判死。
PRIOR_NEGATIVE_RATIO = 0.15
PRIOR_STRENGTH = 4.0


class QualityInspectorAgent(ConsumerAgentBase[BuyerState]):
    """质检员 Agent。

    Example:
        >>> inspector = QualityInspectorAgent(enable_llm=False)
        >>> assessment = await inspector.inspect(candidate)
        >>> assessment.risk_level
        <RiskLevel.HIGH: 'high'>
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化质检员。

        Args:
            enable_llm: 是否允许 LLM 润色结论。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.BUYER_QUALITY_INSPECTOR,
            enable_llm=enable_llm,
            **kwargs,
        )
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """注册提示模板。"""
        self.register_prompt(
            "summary",
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是一名严谨的商品质检顾问。根据给定的差评关键词统计与退货率，"
                        "用一句不超过 60 字的中文点明最大质量风险，并给出一个验货建议。"
                        "只使用输入中出现的事实，不要编造数据。",
                    ),
                    (
                        "human",
                        "商品：{title}\n"
                        "差评占比：{negative_ratio}\n"
                        "缺陷关键词：{defects}\n"
                        "商品退货率：{return_rate}\n"
                        "类目基准退货率：{baseline}\n"
                        "风险等级：{risk}",
                    ),
                ]
            ),
        )

    async def inspect(self, candidate: CandidateProduct) -> QualityAssessment:
        """执行质量口碑分析。

        Args:
            candidate: 候选商品。

        Returns:
            质量评估结果。
        """
        reviews = candidate.reviews or []
        defects = extract_defects(reviews)
        negative_reviews = [
            review
            for review in reviews
            if is_negative_review(review) or has_defect(review)
        ]
        negative_ratio = round(len(negative_reviews) / len(reviews), 4) if reviews else 0.0
        baseline = baseline_return_rate(candidate.category)
        excess_return = None
        if candidate.return_rate is not None:
            excess_return = max(0.0, candidate.return_rate - baseline)

        insight = ReviewInsight(
            total_reviews=len(reviews),
            negative_count=len(negative_reviews),
            negative_ratio=negative_ratio,
            defect_keywords=defects,
            return_rate=candidate.return_rate,
            category_return_rate=baseline,
            evidence_quotes=self._collect_quotes(defects),
        )

        # 小样本的差评占比波动极大，先做贝叶斯平滑再参与打分
        smoothed_ratio = self._smooth_ratio(negative_ratio, len(reviews))
        score = self._score(
            smoothed_ratio, defects, excess_return, has_reviews=bool(reviews)
        )
        risk_level = self._risk_level(
            score, smoothed_ratio, defects, excess_return, bool(reviews)
        )
        insight.risk_level = risk_level
        insight.summary = self._rule_summary(insight, risk_level)

        assessment = QualityAssessment(
            score=score,
            risk_level=risk_level,
            insight=insight,
            warnings=self._build_warnings(insight, excess_return),
        )

        polished = await self.try_generate(
            self.get_prompt("summary"),
            {
                "title": candidate.title,
                "negative_ratio": f"{negative_ratio:.0%}",
                "defects": "、".join(f"{item.keyword}×{item.count}" for item in defects[:5])
                or "无",
                "return_rate": f"{candidate.return_rate:.0%}"
                if candidate.return_rate is not None
                else "无数据",
                "baseline": f"{baseline:.0%}",
                "risk": risk_level.value,
            },
            accept=lambda text: 6 <= len(text) <= 140,
        )
        if polished:
            insight.summary = polished
            assessment.warnings.insert(0, polished)

        return assessment

    # ------------------------------------------------------------------
    # 打分
    # ------------------------------------------------------------------
    @staticmethod
    def _smooth_ratio(negative_ratio: float, total_reviews: int) -> float:
        """对小样本的差评占比做贝叶斯平滑。

        Args:
            negative_ratio: 原始差评占比。
            total_reviews: 样本量。

        Returns:
            平滑后的差评占比，范围 0-1。
        """
        negatives = negative_ratio * total_reviews
        prior = PRIOR_NEGATIVE_RATIO * PRIOR_STRENGTH
        return round((negatives + prior) / (total_reviews + PRIOR_STRENGTH), 4)

    def _score(
        self,
        negative_ratio: float,
        defects: list[Any],
        excess_return: float | None,
        has_reviews: bool,
    ) -> float:
        """计算质量得分。

        Args:
            negative_ratio: 差评占比（已平滑）。
            defects: 缺陷关键词列表。
            excess_return: 退货率超出类目基准的绝对值。
            has_reviews: 是否有评价样本。

        Returns:
            质量得分 0-100。
        """
        if not has_reviews:
            return NEUTRAL_SCORE

        penalty_negative = min(MAX_NEGATIVE_PENALTY, negative_ratio * 100.0 * 0.5)

        penalty_defect = 0.0
        for item in defects[:5]:
            factor = CATEGORY_PENALTY.get(item.category, 1.0)
            # 出现 1 次按 1/2 计，2 次及以上计满
            frequency = min(1.0, item.count / 2.0)
            penalty_defect += item.severity * factor * frequency * 14.0
        penalty_defect = min(MAX_DEFECT_PENALTY, penalty_defect)

        penalty_return = 0.0
        if excess_return is not None and excess_return > 0:
            penalty_return = min(MAX_RETURN_PENALTY, excess_return * 100.0 * 1.5)

        score = 100.0 - penalty_negative - penalty_defect - penalty_return
        return round(max(0.0, min(100.0, score)), 2)

    def _risk_level(
        self,
        score: float,
        negative_ratio: float,
        defects: list[Any],
        excess_return: float | None,
        has_reviews: bool,
    ) -> RiskLevel:
        """判定风险等级。

        Args:
            score: 质量得分。
            negative_ratio: 差评占比。
            defects: 缺陷关键词。
            excess_return: 退货率超出量。
            has_reviews: 是否有评价样本。

        Returns:
            风险等级。
        """
        if not has_reviews:
            return RiskLevel.MEDIUM

        severe_defect = any(item.severity >= 0.9 and item.count >= 2 for item in defects)
        if score < 55 or severe_defect or (excess_return is not None and excess_return > 0.10):
            return RiskLevel.HIGH

        if score < 75 or negative_ratio > 0.25 or any(item.severity >= 0.8 for item in defects):
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    # ------------------------------------------------------------------
    # 文案
    # ------------------------------------------------------------------
    @staticmethod
    def _collect_quotes(defects: list[Any], limit: int = 4) -> list[str]:
        """收集代表性差评片段。

        Args:
            defects: 缺陷关键词列表。
            limit: 最多保留条数。

        Returns:
            原文片段列表。
        """
        quotes: list[str] = []
        for item in defects:
            for quote in item.quotes:
                if quote not in quotes:
                    quotes.append(quote)
                if len(quotes) >= limit:
                    return quotes
        return quotes

    @staticmethod
    def _rule_summary(insight: ReviewInsight, risk_level: RiskLevel) -> str:
        """生成规则版结论。

        Args:
            insight: 差评明细。
            risk_level: 风险等级。

        Returns:
            结论文本。
        """
        if insight.total_reviews == 0:
            return "暂无评价样本，无法评估真实质量，建议查看第三方测评或买家秀。"

        parts = [
            f"样本 {insight.total_reviews} 条评价，差评占比 {insight.negative_ratio:.0%}"
        ]
        if insight.defect_keywords:
            top = insight.defect_keywords[0]
            parts.append(f"最集中的问题是「{top.keyword}」（{top.count} 次，{top.category}类）")
        if insight.return_rate is not None and insight.category_return_rate is not None:
            gap = insight.return_rate - insight.category_return_rate
            compare = "高于" if gap > 0 else "低于"
            parts.append(
                f"退货率 {insight.return_rate:.0%} {compare}类目基准 "
                f"{insight.category_return_rate:.0%}"
            )
        parts.append(f"综合风险 {risk_level.value}")
        return "，".join(parts) + "。"

    @staticmethod
    def _build_warnings(insight: ReviewInsight, excess_return: float | None) -> list[str]:
        """构造风险提示列表。

        Args:
            insight: 差评明细。
            excess_return: 退货率超出量。

        Returns:
            提示文案列表。
        """
        warnings: list[str] = []

        if insight.total_reviews == 0:
            warnings.append("没有可用的评价样本，质量结论仅有参考价值。")
            return warnings

        for item in insight.defect_keywords[:3]:
            warnings.append(
                f"差评高频词「{item.keyword}」出现 {item.count} 次"
                f"（{item.category}类，严重度 {item.severity:.2f}）"
            )

        if insight.return_rate is not None and excess_return and excess_return > 0:
            warnings.append(
                f"退货率 {insight.return_rate:.0%} 高于同类目基准 "
                f"{insight.category_return_rate:.0%}，退换流程可能不轻松"
            )

        if insight.negative_ratio > 0.3:
            warnings.append(
                f"差评占比 {insight.negative_ratio:.0%}，购买前建议重点核对材质与尺码说明"
            )

        return warnings

    async def execute(self, state: BuyerState) -> AgentResult:
        """执行质量分析（工作流节点接口）。

        Args:
            state: 买手团状态。

        Returns:
            包含质量评估的结果对象。
        """
        try:
            assessment = await self.inspect(state.candidate)
            state.quality = assessment
            return AgentResult(
                success=True,
                data={
                    "quality": assessment.model_dump(mode="json"),
                    "agent_trace": AgentTraceItem(
                        agent=self.role.value,
                        status="completed",
                        detail=(
                            f"质量分 {assessment.score:.0f}，风险 {assessment.risk_level.value}，"
                            f"缺陷词 {len(assessment.insight.defect_keywords)} 个"
                        ),
                    ).model_dump(),
                },
            )
        except Exception as exc:
            logger.exception("质检员执行失败")
            return AgentResult(success=False, error=f"质量分析失败: {exc}")
