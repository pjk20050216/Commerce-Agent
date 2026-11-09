"""
比价结果的聚合与解读。

Description:
    「虚拟买手团」与「直播购物分身」共用同一套比价口径，
    避免两处各写一份导致结论不一致。本模块只做纯计算，不发起网络请求，
    因此可被 Agent 复用，也便于单元测试。
2026-11-09
"""

import statistics
from typing import Iterable

from src.config.settings import Settings, get_settings
from src.models.buyer import (
    PriceComparison,
    PriceHistoryPoint,
    PriceQuote,
    PriceVerdict,
)


def _pick_extreme(quotes: list[PriceQuote], *, lowest: bool) -> PriceQuote | None:
    """取报价中的最低价或最高价。

    Args:
        quotes: 报价列表。
        lowest: True 取最低价，False 取最高价。

    Returns:
        对应报价，列表为空时返回 None。
    """
    if not quotes:
        return None
    key = lambda quote: quote.price  # noqa: E731 - 局部短 lambda 提升可读性
    return min(quotes, key=key) if lowest else max(quotes, key=key)


def summarize_history(
    history: Iterable[PriceHistoryPoint],
) -> tuple[float | None, float | None, float | None]:
    """汇总历史价格曲线。

    Args:
        history: 历史价格点。

    Returns:
        ``(历史最低价, 历史最高价, 历史均价)``，无数据时均为 None。
    """
    prices = [point.price for point in history if point.price > 0]
    if not prices:
        return None, None, None
    return min(prices), max(prices), round(statistics.fmean(prices), 2)


def _decide_verdict(
    current: float | None,
    lowest: float | None,
    hist_low: float | None,
    hist_avg: float | None,
    hist_high: float | None,
) -> PriceVerdict:
    """根据当前价与历史价位决定比价结论。

    Args:
        current: 当前价。
        lowest: 全网最低报价。
        hist_low: 历史最低价。
        hist_avg: 历史均价。
        hist_high: 历史最高价。

    Returns:
        比价结论。
    """
    if current is None or current <= 0:
        return PriceVerdict.FAIR

    # 已经打到历史低点（含 3% 容差）→ 明确值得买
    floor = hist_low if hist_low is not None else lowest
    if floor is not None and current <= floor * 1.03:
        return PriceVerdict.GREAT_DEAL

    if hist_avg is not None:
        if current <= hist_avg * 0.92:
            return PriceVerdict.GREAT_DEAL
        if current <= hist_avg * 1.05:
            return PriceVerdict.FAIR
        if hist_high is not None and current > hist_high:
            return PriceVerdict.OVERPRICED
        return PriceVerdict.WAIT

    if lowest is not None:
        if current <= lowest * 1.02:
            return PriceVerdict.GREAT_DEAL
        if current > lowest * 1.35:
            return PriceVerdict.OVERPRICED
        return PriceVerdict.FAIR

    return PriceVerdict.FAIR


def _build_advice(verdict: PriceVerdict, comparison: PriceComparison) -> str:
    """根据比价结论生成一句话建议。

    Args:
        verdict: 比价结论。
        comparison: 比价结果（用于取价位数据）。

    Returns:
        中文建议文案。
    """
    current = comparison.current_price
    hist_low = comparison.historical_low
    hist_avg = comparison.historical_avg

    if verdict is PriceVerdict.GREAT_DEAL:
        if hist_low is not None and current is not None:
            if current < hist_low:
                return (
                    f"当前 ¥{current:.0f} 低于历史最低价 ¥{hist_low:.0f}，"
                    "是本轮监测到的最低点，可以下手。"
                )
            if current <= hist_low * 1.03:
                return f"当前 ¥{current:.0f} 已接近历史最低价 ¥{hist_low:.0f}，是下手的好时机。"
        if hist_avg is not None and current is not None:
            gap = (hist_avg - current) / hist_avg * 100
            return f"当前 ¥{current:.0f} 比近 {len(comparison.history)} 天均价低 {gap:.0f}%，可以下手。"
        return "当前价格处于近期低位，可以下手。"

    if verdict is PriceVerdict.FAIR:
        if comparison.vs_average_pct is not None:
            return (
                f"当前 ¥{current:.0f} 与历史均价基本持平"
                f"（偏离 {comparison.vs_average_pct * 100:+.1f}%），不算亏但也不是最低点。"
            )
        return "当前价格处于合理区间，可按需购买。"

    if verdict is PriceVerdict.WAIT:
        hist_low_text = f"¥{hist_low:.0f}" if hist_low is not None else "更低"
        return (
            f"当前 ¥{current:.0f} 高于历史均价"
            f"（{comparison.vs_average_pct * 100:+.1f}%），建议等到 {hist_low_text} 附近再买。"
        )

    return f"当前 ¥{current:.0f} 处于历史高位，溢价明显，不建议现在购买。"


def build_price_comparison(
    query: str,
    quotes: list[PriceQuote],
    history: list[PriceHistoryPoint],
    current_price: float | None = None,
    source: str = "mock",
    is_mock: bool = False,
    settings: Settings | None = None,
) -> PriceComparison:
    """把原始报价与历史曲线聚合为比价结论。

    Args:
        query: 检索用的商品标题。
        quotes: 各平台报价。
        history: 历史价格曲线。
        current_price: 用户当前看到的价格；缺省时取最低报价。
        source: 数据源标识。
        is_mock: 是否基于模拟数据。
        settings: 配置实例（当前未使用，保留以便后续接入阈值配置）。

    Returns:
        比价结果。
    """
    settings = settings or get_settings()
    sorted_quotes = sorted(quotes, key=lambda quote: quote.price)
    lowest = _pick_extreme(sorted_quotes, lowest=True)
    highest = _pick_extreme(sorted_quotes, lowest=False)

    prices = [quote.price for quote in sorted_quotes]
    average = round(statistics.fmean(prices), 2) if prices else None

    hist_low, hist_high, hist_avg = summarize_history(history)

    effective_current = current_price
    if effective_current is None and lowest is not None:
        effective_current = lowest.price

    vs_lowest = None
    if effective_current is not None and lowest is not None and lowest.price > 0:
        vs_lowest = round((effective_current - lowest.price) / lowest.price, 4)

    vs_average = None
    if effective_current is not None and hist_avg:
        vs_average = round((effective_current - hist_avg) / hist_avg, 4)

    verdict = _decide_verdict(
        effective_current,
        lowest.price if lowest else None,
        hist_low,
        hist_avg,
        hist_high,
    )

    comparison = PriceComparison(
        query=query,
        quotes=sorted_quotes,
        lowest=lowest,
        highest=highest,
        average_price=average,
        current_price=effective_current,
        vs_lowest_pct=vs_lowest,
        vs_average_pct=vs_average,
        history=history,
        historical_low=hist_low,
        historical_high=hist_high,
        historical_avg=hist_avg,
        verdict=verdict,
        advice="",
        source=source,
        is_mock=is_mock,
    )
    comparison.advice = _build_advice(verdict, comparison)
    return comparison


def value_score_from_comparison(comparison: PriceComparison) -> float:
    """把比价结果折算为 0-100 的性价比得分。

    口径：以历史均价为 70 分基准，价格每低于均价 1% 加 1 分，
    每高于均价 1% 扣 1 分；创历史新低额外加 15 分。

    Args:
        comparison: 比价结果。

    Returns:
        性价比得分，范围 0-100。
    """
    score = 70.0
    if comparison.vs_average_pct is not None:
        score = 70.0 - comparison.vs_average_pct * 100.0
    elif comparison.vs_lowest_pct is not None:
        # 无历史曲线时退化为「相对全网最低价」的溢价惩罚
        score = 85.0 - comparison.vs_lowest_pct * 100.0

    current = comparison.current_price
    if (
        current is not None
        and comparison.historical_low is not None
        and current <= comparison.historical_low * 1.01
    ):
        score += 15.0

    return round(max(0.0, min(100.0, score)), 2)
