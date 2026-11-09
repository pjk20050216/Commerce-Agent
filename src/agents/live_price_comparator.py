"""
一键比价 Agent。

Description:
    主播喊出价格的那一刻，自动拉取全网同款报价与历史价格曲线，
    判断「这个价到底值不值得冲」。

    触发条件是字幕里出现了价格（PRICE 类型关键信息），因此本 Agent
    必须在字幕摘要之后执行。
2026-11-09
"""

import logging
from typing import Any

from src.agents.base import AgentResult, AgentRole
from src.agents.consumer_base import ConsumerAgentBase
from src.agents.live_lexicon import extract_prices
from src.agents.price_analysis import build_price_comparison
from src.clients.price_search import PriceSearchError, get_price_search_backend
from src.graph.live_state import LiveState
from src.models.buyer import PriceComparison, PriceVerdict
from src.models.live import KeyPointKind, LiveKeyPoint, LivePriceAlert, PriceTrigger

logger = logging.getLogger(__name__)


class PriceComparatorAgent(ConsumerAgentBase[LiveState]):
    """一键比价 Agent。

    Example:
        >>> agent = PriceComparatorAgent(enable_llm=False)
        >>> alert = await agent.check(points, "纯棉衬衫")
        >>> alert.trigger.price
        99.0
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化比价 Agent。

        Args:
            enable_llm: 是否允许 LLM 增强（当前未使用，保留以统一构造参数）。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.LIVE_PRICE_COMPARATOR,
            enable_llm=enable_llm,
            **kwargs,
        )

    async def check(
        self,
        key_points: list[LiveKeyPoint],
        product_title: str,
    ) -> LivePriceAlert | None:
        """对最近一次报价执行比价。

        Args:
            key_points: 本批抽出的关键信息。
            product_title: 商品标题（用于全网检索）。

        Returns:
            比价提醒；本批没有报价时返回 None。
        """
        trigger_point = self._latest_price_point(key_points)
        if trigger_point is None:
            return None

        prices = extract_prices(trigger_point.text)
        if not prices:
            return None
        price = prices[0]

        trigger = PriceTrigger(
            price=price,
            quote=trigger_point.quote,
            at_seconds=trigger_point.at_seconds,
            product_hint=product_title,
        )

        try:
            backend = get_price_search_backend(self.settings)
            quotes = await backend.search(product_title, reference_price=price)
            history = await backend.history(
                product_title,
                self.settings.price_history_days,
                reference_price=price,
            )
        except PriceSearchError as exc:
            logger.warning("直播比价数据源不可用: %s", exc)
            return LivePriceAlert(
                trigger=trigger,
                comparison=PriceComparison(
                    query=product_title,
                    current_price=price,
                    source="unavailable",
                    advice="比价数据源暂不可用，无法判断主播价是否划算。",
                ),
                advice="比价服务暂不可用，建议以主播公示的优惠力度为准。",
                is_mock=False,
            )
        except Exception as exc:
            logger.exception("直播比价出现未预期异常")
            return LivePriceAlert(
                trigger=trigger,
                comparison=PriceComparison(
                    query=product_title,
                    current_price=price,
                    source="unavailable",
                    advice=f"比价服务异常：{exc}",
                ),
                advice="比价服务异常，请稍后重试。",
                is_mock=False,
            )

        comparison = build_price_comparison(
            query=product_title,
            quotes=quotes,
            history=history,
            current_price=price,
            source=backend.name,
            is_mock=backend.is_mock,
            settings=self.settings,
        )
        return LivePriceAlert(
            trigger=trigger,
            comparison=comparison,
            advice=self._advice(comparison, price),
            is_mock=backend.is_mock,
        )

    @staticmethod
    def _latest_price_point(key_points: list[LiveKeyPoint]) -> LiveKeyPoint | None:
        """取最近一条价格类关键信息。

        Args:
            key_points: 关键信息列表。

        Returns:
            价格关键信息，没有则返回 None。
        """
        price_points = [point for point in key_points if point.kind is KeyPointKind.PRICE]
        return price_points[-1] if price_points else None

    @staticmethod
    def _advice(comparison: PriceComparison, price: float) -> str:
        """生成直播场景下的购买建议。

        Args:
            comparison: 比价结果。
            price: 主播报价。

        Returns:
            建议文本。
        """
        if comparison.verdict is PriceVerdict.GREAT_DEAL:
            if comparison.historical_avg:
                gap = (comparison.historical_avg - price) / comparison.historical_avg * 100
                return (
                    f"主播价 ¥{price:.0f} 低于近期均价 "
                    f"{comparison.historical_avg:.0f} 元约 {gap:.0f}%，符合「值得冲」条件。"
                )
            return f"主播价 ¥{price:.0f} 接近全网最低，可以冲。"

        if comparison.verdict is PriceVerdict.FAIR:
            return f"主播价 ¥{price:.0f} 与全网价格基本持平，按需购买即可。"

        if comparison.verdict is PriceVerdict.WAIT and comparison.historical_avg:
            gap = (price - comparison.historical_avg) / comparison.historical_avg * 100
            return (
                f"主播价 ¥{price:.0f} 高于近期均价 {gap:.0f}%，"
                "不急可以等回落或到其他平台比一比。"
            )

        if comparison.vs_lowest_pct is not None:
            return (
                f"主播价 ¥{price:.0f} 比全网最低价高 "
                f"{comparison.vs_lowest_pct * 100:.0f}%，建议先比价再下单。"
            )
        return f"主播价 ¥{price:.0f} 暂未比到更优价格，请结合优惠力度判断。"

    async def execute(self, state: LiveState) -> AgentResult:
        """执行比价（工作流节点接口）。

        Args:
            state: 直播状态。

        Returns:
            包含比价结果的对象。
        """
        try:
            product = state.current_product or state.title or state.room_id
            alert = await self.check(state.key_points, product)
            state.price_alert = alert
            return AgentResult(
                success=True,
                data={"price_alert": alert.model_dump(mode="json") if alert else None},
            )
        except Exception as exc:
            logger.exception("直播比价失败")
            return AgentResult(success=False, error=f"直播比价失败: {exc}")
