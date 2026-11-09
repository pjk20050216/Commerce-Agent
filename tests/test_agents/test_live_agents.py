"""直播购物分身 Agent 测试。"""

from unittest.mock import patch

import pytest

from src.agents.live_danmaku_sentiment import DanmakuSentimentAgent
from src.agents.live_lexicon import (
    classify_danmaku,
    detect_kinds,
    extract_prices,
    split_sentences,
)
from src.agents.live_price_comparator import PriceComparatorAgent
from src.agents.live_subtitle_summarizer import SubtitleSummarizerAgent
from src.clients.price_search import PriceSearchError, reset_price_search_backend
from src.models.live import DanmakuItem, KeyPointKind, LiveKeyPoint, TranscriptSegment


@pytest.fixture(autouse=True)
def _reset_backend() -> None:
    """清理比价数据源单例。"""
    reset_price_search_backend()
    yield
    reset_price_search_backend()


class TestLiveLexicon:
    """口播与弹幕词库测试。"""

    def test_extract_prices_multiple_forms(self) -> None:
        """应识别 ¥、元、关键词三种写法。"""
        assert extract_prices("到手价199元") == [199.0]
        assert extract_prices("只要 ¥99") == [99.0]
        assert extract_prices("价格：59.9") == [59.9]
        assert extract_prices("没有提到钱") == []

    def test_detect_kinds_returns_single_priority(self) -> None:
        """一句话只保留优先级最高的类型，避免同类噪音。"""
        assert detect_kinds("限量500件") == [KeyPointKind.LIMIT]
        assert detect_kinds("拍一发三") == [KeyPointKind.GIFT]
        assert detect_kinds("倒计时3分钟") == [KeyPointKind.DEADLINE]
        assert detect_kinds("假一赔十") == [KeyPointKind.PROMISE]
        assert detect_kinds("到手价199元") == [KeyPointKind.PRICE]

    def test_split_sentences(self) -> None:
        """按中英文标点切句。"""
        assert split_sentences("限量500件，拍一发三！真的划算") == [
            "限量500件",
            "拍一发三",
            "真的划算",
        ]

    def test_classify_danmaku(self) -> None:
        """弹幕情感极性判定。"""
        assert classify_danmaku("冲了冲了") == "positive"
        assert classify_danmaku("太贵了吧") == "negative"
        assert classify_danmaku("今天天气不错") == "neutral"

    def test_negation_flips_polarity(self) -> None:
        """「没套路」不应被判为负向。"""
        assert classify_danmaku("这个价格没套路") == "neutral"


class TestSubtitleSummarizer:
    """字幕摘要测试。"""

    def test_extract_key_points(self) -> None:
        """从口播中抽出关键信息。"""
        agent = SubtitleSummarizerAgent(enable_llm=False)
        segments = [
            TranscriptSegment(
                start_seconds=0,
                end_seconds=10,
                text="这款衬衫限量500件，拍一发三，到手价199",
            )
        ]
        points = agent.extract(segments)

        kinds = {point.kind for point in points}
        assert KeyPointKind.LIMIT in kinds
        assert KeyPointKind.GIFT in kinds
        assert KeyPointKind.PRICE in kinds
        price_point = next(point for point in points if point.kind is KeyPointKind.PRICE)
        assert price_point.text == "报价 ¥199"
        assert price_point.at_seconds == 0

    def test_extract_deduplicates_repeats(self) -> None:
        """重复播报的同一信息只保留一条。"""
        agent = SubtitleSummarizerAgent(enable_llm=False)
        segments = [
            TranscriptSegment(start_seconds=0, end_seconds=5, text="限量500件"),
            TranscriptSegment(start_seconds=30, end_seconds=35, text="限量500件"),
        ]
        points = agent.extract(segments)

        assert len(points) == 1

    def test_extract_empty(self) -> None:
        """没有有效信息时返回空列表。"""
        agent = SubtitleSummarizerAgent(enable_llm=False)
        assert agent.extract([]) == []


class TestDanmakuSentiment:
    """弹幕情感测试。"""

    def test_analyze_counts_and_tags(self) -> None:
        """统计正负向数量并生成标签。"""
        agent = DanmakuSentimentAgent(enable_llm=False)
        danmaku = [
            DanmakuItem(text="冲了"),
            DanmakuItem(text="已拍"),
            DanmakuItem(text="太贵了"),
            DanmakuItem(text="随便看看"),
        ]
        result = agent.analyze(danmaku, window_seconds=60)

        assert result.total == 4
        assert result.positive == 2
        assert result.negative == 1
        assert result.neutral == 1
        assert result.score > 0
        assert "口碑向好" in result.tags
        assert "价格敏感" in result.tags
        assert result.heat_per_minute == 4.0
        assert result.summary

    def test_analyze_empty_window(self) -> None:
        """没有弹幕时给出中性结果而非报错。"""
        agent = DanmakuSentimentAgent(enable_llm=False)
        result = agent.analyze([], window_seconds=60)

        assert result.total == 0
        assert result.tags == []
        assert "没有弹幕" in result.summary

    def test_negative_window(self) -> None:
        """负向占多数时口碑偏冷。"""
        agent = DanmakuSentimentAgent(enable_llm=False)
        result = agent.analyze(
            [DanmakuItem(text="太贵"), DanmakuItem(text="智商税"), DanmakuItem(text="别买")],
            window_seconds=60,
        )

        assert result.score < 0
        assert "口碑偏冷" in result.tags


class TestPriceComparator:
    """直播比价测试。"""

    @pytest.mark.asyncio
    async def test_check_returns_alert_for_price_point(self) -> None:
        """有报价时应返回比价提醒，并标记模拟数据。"""
        agent = PriceComparatorAgent(enable_llm=False)
        points = [
            LiveKeyPoint(kind=KeyPointKind.PRICE, text="报价 ¥199", quote="到手价199"),
        ]
        alert = await agent.check(points, "纯棉衬衫")

        assert alert is not None
        assert alert.trigger.price == 199.0
        assert alert.trigger.product_hint == "纯棉衬衫"
        assert alert.comparison.current_price == 199.0
        assert alert.is_mock is True
        assert alert.advice

    @pytest.mark.asyncio
    async def test_check_skips_without_price_point(self) -> None:
        """没有报价时不做比价。"""
        agent = PriceComparatorAgent(enable_llm=False)
        points = [LiveKeyPoint(kind=KeyPointKind.LIMIT, text="限量500件")]
        assert await agent.check(points, "纯棉衬衫") is None

    @pytest.mark.asyncio
    async def test_check_degrades_when_source_unavailable(self) -> None:
        """数据源不可用时给出降级说明而不是抛异常。"""
        agent = PriceComparatorAgent(enable_llm=False)
        points = [LiveKeyPoint(kind=KeyPointKind.PRICE, text="报价 ¥199")]
        with patch(
            "src.agents.live_price_comparator.get_price_search_backend",
            side_effect=PriceSearchError("未配置数据源"),
        ):
            alert = await agent.check(points, "纯棉衬衫")

        assert alert is not None
        assert alert.comparison.source == "unavailable"
        assert "不可用" in alert.advice
