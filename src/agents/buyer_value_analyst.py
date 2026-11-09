"""
性价比分析师 Agent。

Description:
    调用全网比价数据源（Elasticsearch 价格索引 / 独立采集服务 / 模拟数据），
    把候选商品当前价与全网报价、历史价格曲线放在一起比较，
    输出「现在该不该买」的结论。

    数据源不可用时不会伪造结论，而是明确返回「比价不可用」，
    由决策官在决策卡上标注降级原因。
2026-11-09
"""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentResult, AgentRole
from src.agents.consumer_base import ConsumerAgentBase
from src.agents.price_analysis import build_price_comparison
from src.clients.price_search import (
    PriceSearchError,
    get_price_search_backend,
)
from src.graph.buyer_state import BuyerState
from src.models.buyer import AgentTraceItem, CandidateProduct, PriceComparison

logger = logging.getLogger(__name__)


class ValueAnalystAgent(ConsumerAgentBase[BuyerState]):
    """性价比分析师 Agent。

    Example:
        >>> analyst = ValueAnalystAgent(enable_llm=False)
        >>> comparison = await analyst.compare(candidate)
        >>> comparison.verdict.value in {"great_deal", "fair", "wait", "overpriced"}
        True
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化性价比分析师。

        Args:
            enable_llm: 是否允许 LLM 润色建议文案。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.BUYER_VALUE_ANALYST,
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
                        "你是一名价格分析师。请根据给定的比价数据，"
                        "用一句不超过 50 字的中文给消费者明确建议（买 / 等 / 换平台）。"
                        "不要编造数据，只使用输入里出现的价格。",
                    ),
                    (
                        "human",
                        "商品：{title}\n"
                        "当前价：{current}\n"
                        "全网最低：{lowest}\n"
                        "历史最低：{hist_low}\n"
                        "历史均价：{hist_avg}\n"
                        "结论：{verdict}\n"
                        "规则建议：{advice}",
                    ),
                ]
            ),
        )

    async def compare(
        self,
        candidate: CandidateProduct,
        history_days: int | None = None,
        current_price: float | None = None,
    ) -> PriceComparison:
        """执行全网比价。

        Args:
            candidate: 候选商品。
            history_days: 历史曲线回看天数，缺省取配置值。
            current_price: 显式指定的当前价，缺省取商品价格；
                两者都没有有效值（<=0）时以全网最低价为基准。

        Returns:
            比价结果；数据源不可用时返回带降级说明的空结果。
        """
        days = history_days or self.settings.price_history_days

        effective_price = current_price
        if effective_price is None and candidate.price > 0:
            effective_price = candidate.price

        try:
            backend = get_price_search_backend(self.settings)
        except PriceSearchError as exc:
            logger.warning("比价数据源初始化失败: %s", exc)
            return self._unavailable(candidate, str(exc))

        try:
            quotes = await backend.search(candidate.title, reference_price=effective_price)
            history = await backend.history(
                candidate.title, days, reference_price=effective_price
            )
        except PriceSearchError as exc:
            logger.warning("比价数据源调用失败: %s", exc)
            return self._unavailable(candidate, str(exc))
        except Exception as exc:  # 兜底：数据源实现自带的异常类型不统一
            logger.exception("比价数据源出现未预期异常")
            return self._unavailable(candidate, str(exc))

        comparison = build_price_comparison(
            query=candidate.title,
            quotes=quotes,
            history=history,
            current_price=effective_price,
            source=backend.name,
            is_mock=backend.is_mock,
            settings=self.settings,
        )

        polished = await self.try_generate(
            self.get_prompt("advice"),
            {
                "title": candidate.title,
                "current": (
                    f"¥{effective_price:.0f}" if effective_price is not None else "未知"
                ),
                "lowest": self._format_quote(comparison),
                "hist_low": self._format_price(comparison.historical_low),
                "hist_avg": self._format_price(comparison.historical_avg),
                "verdict": comparison.verdict.value,
                "advice": comparison.advice,
            },
            accept=lambda text: 4 <= len(text) <= 120,
        )
        if polished:
            comparison.advice = polished

        return comparison

    def _unavailable(self, candidate: CandidateProduct, reason: str) -> PriceComparison:
        """构造「比价不可用」的结果。

        Args:
            candidate: 候选商品。
            reason: 不可用原因。

        Returns:
            标记了降级说明的比价结果。
        """
        return PriceComparison(
            query=candidate.title,
            current_price=candidate.price,
            source="unavailable",
            is_mock=False,
            advice=f"比价数据源暂不可用（{reason}），本次决策未纳入价格维度参考。",
        )

    @staticmethod
    def _format_price(value: float | None) -> str:
        """格式化价格。

        Args:
            value: 价格。

        Returns:
            形如 ``¥199`` 的文本，缺失时返回「未知」。
        """
        return f"¥{value:.0f}" if value is not None else "未知"

    def _format_quote(self, comparison: PriceComparison) -> str:
        """格式化最低价报价。

        Args:
            comparison: 比价结果。

        Returns:
            形如 ``¥199（京东）`` 的文本。
        """
        if comparison.lowest is None:
            return "未知"
        return f"¥{comparison.lowest.price:.0f}（{comparison.lowest.platform}）"

    async def execute(self, state: BuyerState) -> AgentResult:
        """执行比价（工作流节点接口）。

        Args:
            state: 买手团状态。

        Returns:
            包含比价结果的结果对象。
        """
        try:
            comparison = await self.compare(state.candidate)
            state.price_comparison = comparison

            if comparison.source == "unavailable":
                status, detail = "fallback", comparison.advice
            else:
                status = "completed"
                detail = (
                    f"数据源 {comparison.source}"
                    f"{'（模拟）' if comparison.is_mock else ''}，"
                    f"覆盖 {len(comparison.quotes)} 个平台，结论 {comparison.verdict.value}"
                )

            return AgentResult(
                success=True,
                data={
                    "price_comparison": comparison.model_dump(mode="json"),
                    "agent_trace": AgentTraceItem(
                        agent=self.role.value, status=status, detail=detail
                    ).model_dump(),
                },
            )
        except Exception as exc:
            logger.exception("性价比分析师执行失败")
            return AgentResult(success=False, error=f"比价失败: {exc}")
