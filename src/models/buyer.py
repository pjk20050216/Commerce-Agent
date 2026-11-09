"""
虚拟买手团领域模型。

Description:
    定义消费者侧「虚拟买手团」的输入与产出结构：
    - 用户画像与风格偏好（风格顾问 Agent 产出）
    - 全网比价与历史价格曲线（性价比分析师 Agent 产出）
    - 差评关键词与退货风险（质检员 Agent 产出）
    - 买手决策卡（综合评分 + 推荐理由 + 风险预警）
2026-11-09
"""

from datetime import date as DateOnly
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class BrowsingAction(str, Enum):
    """用户行为类型。"""

    VIEW = "view"
    FAVORITE = "favorite"
    CART = "cart"
    PURCHASE = "purchase"


class StyleDimension(BaseModel):
    """单个风格维度的偏好强度。

    Attributes:
        name: 风格名称，如「极简风」「高街潮牌」。
        weight: 归一化权重 0-1，越大代表偏好越强。
        evidence: 支撑该判断的用户行为摘要。
    """

    name: str = Field(..., description="风格名称")
    weight: float = Field(..., ge=0, le=1, description="偏好权重")
    evidence: list[str] = Field(default_factory=list, description="支撑证据")


class PriceBand(BaseModel):
    """用户的价格带画像。

    Attributes:
        min_price: 历史浏览/购买的最低单价。
        max_price: 历史浏览/购买的最高单价。
        avg_price: 平均单价。
        preferred_price: 当前候选商品价格（用于判断是否偏离价格带）。
    """

    min_price: float | None = Field(default=None, ge=0, description="价格带下沿")
    max_price: float | None = Field(default=None, ge=0, description="价格带上沿")
    avg_price: float | None = Field(default=None, ge=0, description="价格带均值")
    preferred_price: float | None = Field(default=None, ge=0, description="候选商品价格")


class BrowsingRecord(BaseModel):
    """一条用户行为记录。

    Attributes:
        item_id: 商品标识。
        title: 商品标题。
        category: 类目。
        tags: 商品标签（风格、材质等）。
        price: 价格。
        action: 行为类型。
        occurred_at: 发生时间。
    """

    item_id: str = Field(..., description="商品标识")
    title: str = Field(..., description="商品标题")
    category: str | None = Field(default=None, description="类目")
    brand: str | None = Field(default=None, description="品牌")
    tags: list[str] = Field(default_factory=list, description="商品标签")
    price: float | None = Field(default=None, ge=0, description="价格")
    action: BrowsingAction = Field(default=BrowsingAction.VIEW, description="行为类型")
    occurred_at: datetime | None = Field(default=None, description="发生时间")


class StyleProfile(BaseModel):
    """风格顾问 Agent 的产出：用户审美画像。

    Attributes:
        user_id: 用户标识。
        dominant_styles: 偏好风格列表（按权重降序）。
        price_band: 价格带画像。
        preferred_categories: 高频类目。
        brand_affinity: 品牌偏好。
        confidence: 画像置信度 0-1，样本不足时偏低。
        based_on_records: 参与计算的记录数。
        summary: 一句话画像描述。
    """

    user_id: str = Field(..., description="用户标识")
    dominant_styles: list[StyleDimension] = Field(
        default_factory=list, description="偏好风格（按权重降序）"
    )
    price_band: PriceBand = Field(default_factory=PriceBand, description="价格带画像")
    preferred_categories: list[str] = Field(default_factory=list, description="高频类目")
    brand_affinity: list[str] = Field(default_factory=list, description="品牌偏好")
    confidence: float = Field(default=0, ge=0, le=1, description="画像置信度")
    based_on_records: int = Field(default=0, ge=0, description="参与计算的记录数")
    summary: str = Field(default="", description="画像摘要")


class CandidateProduct(BaseModel):
    """待决策的候选商品。

    Attributes:
        title: 商品标题。
        price: 当前价格。
        category: 类目。
        brand: 品牌。
        platform: 来源平台。
        url: 商品链接。
        specs: 规格（如颜色、尺码、容量）。
        tags: 标签（用于风格匹配）。
        reviews: 用户评价文本（用于差评挖掘）。
        return_rate: 该商品退货率 0-1（如有）。
        total_reviews: 评价总数（用于计算差评占比）。
    """

    title: str = Field(..., min_length=1, description="商品标题")
    price: float = Field(..., ge=0, description="当前价格")
    category: str | None = Field(default=None, description="类目")
    brand: str | None = Field(default=None, description="品牌")
    platform: str | None = Field(default=None, description="来源平台")
    url: str | None = Field(default=None, description="商品链接")
    specs: dict[str, str] = Field(default_factory=dict, description="规格")
    tags: list[str] = Field(default_factory=list, description="标签")
    reviews: list[str] = Field(default_factory=list, description="评价文本")
    return_rate: float | None = Field(default=None, ge=0, le=1, description="退货率")
    total_reviews: int | None = Field(default=None, ge=0, description="评价总数")


class PriceQuote(BaseModel):
    """单条全网报价。

    Attributes:
        platform: 平台名称。
        title: 商品标题。
        price: 到手价。
        currency: 币种。
        seller: 店铺名。
        url: 链接。
        is_mock: 是否为模拟数据（未接入真实数据源时为 True）。
        fetched_at: 抓取时间。
    """

    platform: str = Field(..., description="平台名称")
    title: str = Field(..., description="商品标题")
    price: float = Field(..., ge=0, description="到手价")
    currency: str = Field(default="CNY", description="币种")
    seller: str | None = Field(default=None, description="店铺名")
    url: str | None = Field(default=None, description="链接")
    is_mock: bool = Field(default=False, description="是否为模拟数据")
    fetched_at: datetime | None = Field(default=None, description="抓取时间")


class PriceHistoryPoint(BaseModel):
    """历史价格曲线上的一个点。"""

    date: DateOnly = Field(..., description="日期")
    price: float = Field(..., ge=0, description="当日最低价")


class PriceVerdict(str, Enum):
    """比价结论。"""

    GREAT_DEAL = "great_deal"
    FAIR = "fair"
    WAIT = "wait"
    OVERPRICED = "overpriced"


class PriceComparison(BaseModel):
    """性价比分析师 Agent 的产出：全网比价结果。

    Attributes:
        query: 检索用的商品标题。
        quotes: 各平台报价。
        lowest: 最低价报价。
        highest: 最高价报价。
        average_price: 均价。
        current_price: 用户看到的当前价。
        vs_lowest_pct: 当前价相对最低价的溢价比例（正数代表更贵）。
        vs_average_pct: 当前价相对均价的偏离比例。
        history: 历史价格曲线。
        historical_low: 历史最低价。
        historical_high: 历史最高价。
        historical_avg: 历史均价。
        verdict: 比价结论。
        advice: 一句话购买建议。
        source: 数据源标识（es/crawler/mock）。
        is_mock: 是否基于模拟数据。
    """

    query: str = Field(..., description="检索商品标题")
    quotes: list[PriceQuote] = Field(default_factory=list, description="各平台报价")
    lowest: PriceQuote | None = Field(default=None, description="最低价报价")
    highest: PriceQuote | None = Field(default=None, description="最高价报价")
    average_price: float | None = Field(default=None, ge=0, description="均价")
    current_price: float | None = Field(default=None, ge=0, description="当前价")
    vs_lowest_pct: float | None = Field(default=None, description="相对最低价溢价比例")
    vs_average_pct: float | None = Field(default=None, description="相对均价偏离比例")
    history: list[PriceHistoryPoint] = Field(default_factory=list, description="历史价格曲线")
    historical_low: float | None = Field(default=None, ge=0, description="历史最低价")
    historical_high: float | None = Field(default=None, ge=0, description="历史最高价")
    historical_avg: float | None = Field(default=None, ge=0, description="历史均价")
    verdict: PriceVerdict = Field(default=PriceVerdict.FAIR, description="比价结论")
    advice: str = Field(default="", description="购买建议")
    source: str = Field(default="mock", description="数据源标识")
    is_mock: bool = Field(default=False, description="是否基于模拟数据")


class DefectKeyword(BaseModel):
    """差评中挖掘出的缺陷关键词。

    Attributes:
        keyword: 关键词，如「掉色」。
        category: 缺陷类型（做工/材质/尺码/物流/色差/功能/服务）。
        count: 出现次数。
        severity: 严重度 0-1。
        quotes: 命中的原始差评片段。
    """

    keyword: str = Field(..., description="缺陷关键词")
    category: str = Field(..., description="缺陷类型")
    count: int = Field(default=0, ge=0, description="出现次数")
    severity: float = Field(default=0, ge=0, le=1, description="严重度")
    quotes: list[str] = Field(default_factory=list, description="命中的原始片段")


class RiskLevel(str, Enum):
    """风险等级。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewInsight(BaseModel):
    """质检员 Agent 的产出：差评与退货风险分析。

    Attributes:
        total_reviews: 参与分析的评价数。
        negative_count: 差评数。
        negative_ratio: 差评占比。
        defect_keywords: 缺陷关键词列表（按严重度降序）。
        return_rate: 商品退货率。
        category_return_rate: 同类目基准退货率。
        risk_level: 综合风险等级。
        evidence_quotes: 代表性差评片段。
        summary: 一句话结论。
    """

    total_reviews: int = Field(default=0, ge=0, description="参与分析的评价数")
    negative_count: int = Field(default=0, ge=0, description="差评数")
    negative_ratio: float = Field(default=0, ge=0, le=1, description="差评占比")
    defect_keywords: list[DefectKeyword] = Field(
        default_factory=list, description="缺陷关键词"
    )
    return_rate: float | None = Field(default=None, ge=0, le=1, description="商品退货率")
    category_return_rate: float | None = Field(
        default=None, ge=0, le=1, description="同类目基准退货率"
    )
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="综合风险等级")
    evidence_quotes: list[str] = Field(default_factory=list, description="代表性差评片段")
    summary: str = Field(default="", description="一句话结论")


class QualityAssessment(BaseModel):
    """质检员 Agent 的完整评估。

    Attributes:
        score: 质量得分 0-100，越高越可靠。
        risk_level: 风险等级。
        insight: 差评明细。
        warnings: 面向用户的风险提示。
    """

    score: float = Field(default=0, ge=0, le=100, description="质量得分")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="风险等级")
    insight: ReviewInsight = Field(default_factory=ReviewInsight, description="差评明细")
    warnings: list[str] = Field(default_factory=list, description="风险提示")


class WeightedScore(BaseModel):
    """加权评分明细。

    Attributes:
        style_fit: 风格匹配分 0-100。
        value_score: 性价比分 0-100。
        quality_score: 质量口碑分 0-100。
        weights: 实际使用的归一化权重。
        overall: 加权总分 0-100（已扣除风险惩罚）。
    """

    style_fit: float = Field(..., ge=0, le=100, description="风格匹配分")
    value_score: float = Field(..., ge=0, le=100, description="性价比分")
    quality_score: float = Field(..., ge=0, le=100, description="质量口碑分")
    weights: dict[str, float] = Field(default_factory=dict, description="归一化权重")
    overall: float = Field(..., ge=0, le=100, description="加权总分")


class DecisionWarning(BaseModel):
    """决策卡上的单条风险预警。

    Attributes:
        kind: 风险类型（price/quality/style/logistics）。
        severity: 严重度。
        message: 提示文案。
        evidence: 支撑证据。
    """

    kind: str = Field(..., description="风险类型")
    severity: RiskLevel = Field(default=RiskLevel.LOW, description="严重度")
    message: str = Field(..., description="提示文案")
    evidence: str | None = Field(default=None, description="支撑证据")


class Recommendation(str, Enum):
    """买手团最终建议。"""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    CONSIDER = "consider"
    AVOID = "avoid"


class AgentTraceItem(BaseModel):
    """决策卡上的单个 Agent 执行痕迹。

    Attributes:
        agent: Agent 名称。
        status: 执行状态（completed/fallback）。
        detail: 简要说明。
    """

    agent: str = Field(..., description="Agent 名称")
    status: str = Field(default="completed", description="执行状态")
    detail: str = Field(default="", description="简要说明")


class BuyerDecisionCard(BaseModel):
    """虚拟买手团的最终产出：买手决策卡。

    Attributes:
        card_id: 决策卡标识。
        user_id: 用户标识。
        candidate: 候选商品。
        style_profile: 风格画像。
        price_comparison: 全网比价结果。
        quality: 质量口碑评估。
        score: 加权评分明细。
        recommendation: 最终建议。
        reasons: 推荐理由。
        warnings: 风险预警。
        buy_advice: 一句话行动建议。
        is_mock_data: 是否包含模拟外部数据。
        generated_at: 生成时间。
        agent_trace: 各 Agent 执行痕迹。
    """

    card_id: str = Field(..., description="决策卡标识")
    user_id: str = Field(..., description="用户标识")
    candidate: CandidateProduct = Field(..., description="候选商品")
    style_profile: StyleProfile = Field(..., description="风格画像")
    price_comparison: PriceComparison = Field(..., description="全网比价")
    quality: QualityAssessment = Field(..., description="质量口碑评估")
    score: WeightedScore = Field(..., description="加权评分")
    recommendation: Recommendation = Field(..., description="最终建议")
    reasons: list[str] = Field(default_factory=list, description="推荐理由")
    warnings: list[DecisionWarning] = Field(default_factory=list, description="风险预警")
    buy_advice: str = Field(default="", description="行动建议")
    is_mock_data: bool = Field(default=False, description="是否包含模拟外部数据")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")
    agent_trace: list[AgentTraceItem] = Field(default_factory=list, description="Agent 执行痕迹")
