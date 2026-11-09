"""虚拟买手团 Agent 测试。"""

from unittest.mock import patch

import pytest

from src.agents.buyer_decision_maker import DecisionMakerAgent
from src.agents.buyer_quality_inspector import QualityInspectorAgent
from src.agents.buyer_review_lexicon import (
    baseline_return_rate,
    extract_defects,
    has_defect,
    is_negative_review,
)
from src.agents.buyer_style_advisor import StyleAdvisorAgent
from src.agents.buyer_value_analyst import ValueAnalystAgent
from src.agents.price_analysis import (
    build_price_comparison,
    summarize_history,
    value_score_from_comparison,
)
from src.clients.price_search import (
    MockPriceSearchBackend,
    PriceSearchError,
    reset_price_search_backend,
)
from src.models.buyer import (
    BrowsingAction,
    BrowsingRecord,
    CandidateProduct,
    PriceHistoryPoint,
    PriceQuote,
    PriceVerdict,
    QualityAssessment,
    Recommendation,
    ReviewInsight,
    RiskLevel,
    StyleProfile,
)

from datetime import date, timedelta


@pytest.fixture(autouse=True)
def _reset_backend() -> None:
    """每个用例前后清理比价数据源单例，避免用例相互污染。"""
    reset_price_search_backend()
    yield
    reset_price_search_backend()


@pytest.fixture
def candidate() -> CandidateProduct:
    """带差评样本的候选商品。"""
    return CandidateProduct(
        title="极简风纯色棉质宽松衬衫",
        price=199.0,
        category="女装",
        tags=["极简", "纯色", "棉"],
        reviews=["掉色严重", "尺码偏小", "面料起球", "版型不错"],
        return_rate=0.23,
    )


@pytest.fixture
def history() -> list[BrowsingRecord]:
    """用户历史行为。"""
    return [
        BrowsingRecord(
            item_id="1",
            title="简约纯色T恤",
            category="女装",
            tags=["极简", "纯色"],
            price=89.0,
            action=BrowsingAction.PURCHASE,
        ),
        BrowsingRecord(
            item_id="2",
            title="基础款衬衫",
            category="女装",
            tags=["极简"],
            price=159.0,
            action=BrowsingAction.CART,
        ),
        BrowsingRecord(
            item_id="3",
            title="高街宽松卫衣",
            category="女装",
            tags=["高街", "宽松"],
            price=299.0,
            action=BrowsingAction.VIEW,
        ),
    ]


class TestStyleAdvisor:
    """风格顾问测试。"""

    @pytest.mark.asyncio
    async def test_build_profile_from_history(
        self, history: list[BrowsingRecord], candidate: CandidateProduct
    ) -> None:
        """应从行为记录中识别出主导风格与价格带。"""
        advisor = StyleAdvisorAgent(enable_llm=False)
        profile = await advisor.build_profile("u1", history, candidate)

        assert profile.user_id == "u1"
        assert profile.dominant_styles
        assert profile.dominant_styles[0].name == "极简风"
        assert profile.dominant_styles[0].evidence
        assert profile.price_band.min_price == 89.0
        assert profile.price_band.max_price == 299.0
        assert profile.price_band.preferred_price == 199.0
        assert profile.confidence > 0

    @pytest.mark.asyncio
    async def test_empty_history_degrades_gracefully(self) -> None:
        """无样本时画像为空且置信度为 0，不应抛异常。"""
        advisor = StyleAdvisorAgent(enable_llm=False)
        profile = await advisor.build_profile("u2", [])

        assert profile.dominant_styles == []
        assert profile.confidence == 0
        assert "暂无行为样本" in profile.summary

    @pytest.mark.asyncio
    async def test_score_fit_rewards_matching_style(
        self, history: list[BrowsingRecord], candidate: CandidateProduct
    ) -> None:
        """标签命中的商品风格分应高于不命中的商品。"""
        advisor = StyleAdvisorAgent(enable_llm=False)
        profile = await advisor.build_profile("u1", history, candidate)

        matched, reasons = advisor.score_fit(profile, candidate)
        mismatched, _ = advisor.score_fit(
            profile,
            CandidateProduct(title="甜美仙女蕾丝连衣裙", price=299.0, tags=["甜美", "蕾丝"]),
        )

        assert matched > mismatched
        assert matched >= 90
        assert any("极简风" in reason for reason in reasons)

    @pytest.mark.asyncio
    async def test_score_fit_neutral_without_profile(self) -> None:
        """画像为空时按中性 60 分处理。"""
        advisor = StyleAdvisorAgent(enable_llm=False)
        score, reasons = advisor.score_fit(
            StyleProfile(user_id="u3"), CandidateProduct(title="任意商品", price=10.0)
        )

        assert score == 60.0
        assert "样本不足" in reasons[0]


class TestReviewLexicon:
    """差评词库测试。"""

    def test_extract_defects_counts_and_sorts(self) -> None:
        """关键词应被归类并按「次数 × 严重度」排序。"""
        reviews = ["掉色很严重，洗一次就掉色", "面料起球", "整体还行"]
        defects = extract_defects(reviews)

        assert defects
        assert defects[0].keyword == "掉色"
        assert defects[0].count == 2
        assert defects[0].category == "材质"
        assert defects[0].quotes

    def test_has_defect_detects_plain_complaint(self) -> None:
        """「掉色严重」不带情绪词，但应被判定为缺陷。"""
        assert has_defect("掉色严重") is True
        assert has_defect("版型很好") is False

    def test_negative_marker(self) -> None:
        """情绪词判定。"""
        assert is_negative_review("太差了，后悔买") is True
        assert is_negative_review("质量很好，推荐") is False

    def test_baseline_return_rate(self) -> None:
        """类目退货率基准，未知类目走默认值。"""
        assert baseline_return_rate("女装") == 0.20
        assert baseline_return_rate(None) == 0.10
        assert baseline_return_rate("未知类目XYZ") == 0.10


class TestQualityInspector:
    """质检员测试。"""

    @pytest.mark.asyncio
    async def test_inspect_flags_defects_and_return_rate(
        self, candidate: CandidateProduct
    ) -> None:
        """差评与偏高退货率应拉低质量分并给出预警。"""
        inspector = QualityInspectorAgent(enable_llm=False)
        assessment = await inspector.inspect(candidate)

        assert assessment.insight.total_reviews == 4
        assert assessment.insight.negative_count == 3
        assert assessment.insight.negative_ratio == 0.75
        assert assessment.insight.defect_keywords[0].keyword == "掉色"
        assert assessment.score < 75
        assert assessment.warnings

    @pytest.mark.asyncio
    async def test_inspect_without_reviews_is_neutral(self) -> None:
        """没有评价时不臆造缺陷，给中性分并提示样本缺失。"""
        inspector = QualityInspectorAgent(enable_llm=False)
        assessment = await inspector.inspect(
            CandidateProduct(title="新品无评价", price=99.0, category="数码")
        )

        assert assessment.score == 70.0
        assert assessment.risk_level is RiskLevel.MEDIUM
        assert any("评价样本" in warning for warning in assessment.warnings)

    @pytest.mark.asyncio
    async def test_clean_reviews_scored_high(self) -> None:
        """干净的正面评价应得到低风险。"""
        inspector = QualityInspectorAgent(enable_llm=False)
        assessment = await inspector.inspect(
            CandidateProduct(
                title="纯棉T恤",
                price=89.0,
                category="女装",
                reviews=["质量很好", "版型喜欢", "物流很快"],
                return_rate=0.05,
            )
        )

        assert assessment.score >= 80
        assert assessment.risk_level is RiskLevel.LOW


class TestPriceAnalysis:
    """比价聚合测试。"""

    def test_summarize_history(self) -> None:
        """历史曲线汇总。"""
        today = date.today()
        history = [
            PriceHistoryPoint(date=today - timedelta(days=1), price=100.0),
            PriceHistoryPoint(date=today, price=120.0),
        ]
        low, high, avg = summarize_history(history)
        assert low == 100.0
        assert high == 120.0
        assert avg == 110.0

    def test_great_deal_when_below_history(self) -> None:
        """当前价低于历史最低价 → great_deal。"""
        today = date.today()
        comparison = build_price_comparison(
            query="衬衫",
            quotes=[PriceQuote(platform="京东", title="衬衫", price=150.0)],
            history=[PriceHistoryPoint(date=today, price=180.0)],
            current_price=140.0,
            source="mock",
            is_mock=True,
        )

        assert comparison.verdict is PriceVerdict.GREAT_DEAL
        assert "低于历史最低价" in comparison.advice
        assert value_score_from_comparison(comparison) >= 90

    def test_overpriced_when_above_history(self) -> None:
        """当前价高于历史最高价 → overpriced。"""
        today = date.today()
        comparison = build_price_comparison(
            query="衬衫",
            quotes=[PriceQuote(platform="京东", title="衬衫", price=150.0)],
            history=[PriceHistoryPoint(date=today, price=120.0)],
            current_price=300.0,
            source="mock",
        )

        assert comparison.verdict is PriceVerdict.OVERPRICED
        assert value_score_from_comparison(comparison) < 40


class TestValueAnalyst:
    """性价比分析师测试。"""

    @pytest.mark.asyncio
    async def test_compare_with_mock_source_is_flagged(
        self, candidate: CandidateProduct
    ) -> None:
        """模拟数据源必须带上 is_mock 标记。"""
        analyst = ValueAnalystAgent(enable_llm=False)
        comparison = await analyst.compare(candidate)

        assert comparison.source == "mock"
        assert comparison.is_mock is True
        assert comparison.quotes
        assert comparison.lowest is not None
        assert comparison.history
        assert comparison.current_price == candidate.price

    @pytest.mark.asyncio
    async def test_compare_degrades_when_source_unavailable(
        self, candidate: CandidateProduct
    ) -> None:
        """数据源不可用时应返回降级结果而不是抛异常。"""
        analyst = ValueAnalystAgent(enable_llm=False)
        with patch(
            "src.agents.buyer_value_analyst.get_price_search_backend",
            side_effect=PriceSearchError("未配置数据源"),
        ):
            comparison = await analyst.compare(candidate)

        assert comparison.source == "unavailable"
        assert comparison.quotes == []
        assert "不可用" in comparison.advice

    @pytest.mark.asyncio
    async def test_mock_backend_is_deterministic(self) -> None:
        """同一标题的模拟报价应可复现。"""
        backend = MockPriceSearchBackend()
        first = await backend.search("纯棉衬衫", reference_price=199.0)
        second = await backend.search("纯棉衬衫", reference_price=199.0)

        assert [item.price for item in first] == [item.price for item in second]


class TestDecisionMaker:
    """决策官测试。"""

    @pytest.mark.asyncio
    async def test_card_includes_components_and_warnings(
        self, candidate: CandidateProduct
    ) -> None:
        """决策卡应包含三路结论、加权明细与预警。"""
        advisor = StyleAdvisorAgent(enable_llm=False)
        inspector = QualityInspectorAgent(enable_llm=False)
        analyst = ValueAnalystAgent(enable_llm=False)
        maker = DecisionMakerAgent(enable_llm=False)

        profile = await advisor.build_profile("u1", [], candidate)
        fit, _ = advisor.score_fit(profile, candidate)
        comparison = await analyst.compare(candidate)
        quality = await inspector.inspect(candidate)

        card = await maker.decide("u1", candidate, profile, fit, comparison, quality)

        assert card.card_id.startswith("card_")
        assert 0 <= card.score.overall <= 100
        assert abs(sum(card.score.weights.values()) - 1.0) < 1e-6
        assert card.recommendation in set(Recommendation)
        assert card.reasons
        assert card.is_mock_data is True
        # 模拟数据必须明确提示，避免用户把演示价当真实行情
        assert any(warning.kind == "data" for warning in card.warnings)

    @pytest.mark.asyncio
    async def test_high_risk_lowers_score(self) -> None:
        """同等分项下，高风险质量评估应拉低综合分。"""
        maker = DecisionMakerAgent(enable_llm=False)
        candidate = CandidateProduct(title="普通衬衫", price=199.0)
        profile = StyleProfile(user_id="u1")
        comparison = build_price_comparison(
            query="衬衫",
            quotes=[PriceQuote(platform="京东", title="衬衫", price=199.0)],
            history=[],
            current_price=199.0,
            source="es",
        )

        low_risk = QualityAssessment(
            score=90.0,
            risk_level=RiskLevel.LOW,
            insight=ReviewInsight(total_reviews=10),
        )
        high_risk = QualityAssessment(
            score=90.0,
            risk_level=RiskLevel.HIGH,
            insight=ReviewInsight(total_reviews=10),
        )

        low_card = await maker.decide("u1", candidate, profile, 80.0, comparison, low_risk)
        high_card = await maker.decide("u1", candidate, profile, 80.0, comparison, high_risk)

        assert high_card.score.overall < low_card.score.overall

    @pytest.mark.asyncio
    async def test_threshold_mapping(self) -> None:
        """评分档位映射符合配置阈值。"""
        maker = DecisionMakerAgent(enable_llm=False)
        assert maker._recommendation(90.0) is Recommendation.STRONG_BUY
        assert maker._recommendation(75.0) is Recommendation.BUY
        assert maker._recommendation(65.0) is Recommendation.CONSIDER
        assert maker._recommendation(30.0) is Recommendation.AVOID

    @pytest.mark.asyncio
    async def test_missing_inputs_still_produce_card(self) -> None:
        """三路结论全部缺失时也应产出保守的决策卡。"""
        maker = DecisionMakerAgent(enable_llm=False)
        card = await maker.decide(
            "u1", CandidateProduct(title="未知商品", price=10.0), None, None, None, None
        )

        assert card.recommendation is Recommendation.AVOID
        assert any(warning.kind == "data" for warning in card.warnings)
