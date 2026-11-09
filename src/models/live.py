"""
直播购物分身领域模型。

Description:
    定义「直播购物分身」的输入与产出结构：
    - 口播字幕片段与弹幕流
    - 关键信息提取（价格 / 限量 / 赠品 / 时效 / 规格 / 承诺）
    - 弹幕情感与热度分析
    - 主播报价触发的一键比价与历史价格曲线
2026-11-09
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.models.buyer import PriceComparison


class TranscriptSegment(BaseModel):
    """一段口播字幕。

    Attributes:
        start_seconds: 相对开播时间的起始秒。
        end_seconds: 结束秒。
        text: 字幕文本。
        speaker: 主播/助播标识。
    """

    start_seconds: float = Field(..., ge=0, description="起始秒")
    end_seconds: float = Field(..., ge=0, description="结束秒")
    text: str = Field(..., min_length=1, description="字幕文本")
    speaker: str = Field(default="主播", description="说话人")


class DanmakuItem(BaseModel):
    """一条弹幕。

    Attributes:
        text: 弹幕文本。
        sent_at: 发送时间。
        user: 发送者标识。
        likes: 点赞数。
    """

    text: str = Field(..., min_length=1, description="弹幕文本")
    sent_at: datetime | None = Field(default=None, description="发送时间")
    user: str | None = Field(default=None, description="发送者")
    likes: int = Field(default=0, ge=0, description="点赞数")


class KeyPointKind(str, Enum):
    """关键信息类型。"""

    PRICE = "price"
    LIMIT = "limit"
    GIFT = "gift"
    DEADLINE = "deadline"
    SPEC = "spec"
    PROMISE = "promise"
    OTHER = "other"


class LiveKeyPoint(BaseModel):
    """从口播中提取的一条关键信息。

    Attributes:
        kind: 信息类型。
        text: 归一化后的信息。
        quote: 原始口播片段。
        confidence: 置信度。
        at_seconds: 出现时间（秒）。
    """

    kind: KeyPointKind = Field(..., description="信息类型")
    text: str = Field(..., description="归一化信息")
    quote: str = Field(default="", description="原始口播片段")
    confidence: float = Field(default=0.6, ge=0, le=1, description="置信度")
    at_seconds: float | None = Field(default=None, ge=0, description="出现时间（秒）")


class SentimentBreakdown(BaseModel):
    """弹幕情感与热度分析结果。

    Attributes:
        total: 参与统计的弹幕数。
        positive: 正向弹幕数。
        negative: 负向弹幕数。
        neutral: 中性弹幕数。
        score: 情感得分 -1 到 1。
        heat_per_minute: 每分钟弹幕数（热度）。
        top_positive_phrases: 高频正向短语。
        top_negative_phrases: 高频负向短语。
        tags: 大众口碑标签。
        summary: 一句话结论。
    """

    total: int = Field(default=0, ge=0, description="弹幕总数")
    positive: int = Field(default=0, ge=0, description="正向弹幕数")
    negative: int = Field(default=0, ge=0, description="负向弹幕数")
    neutral: int = Field(default=0, ge=0, description="中性弹幕数")
    score: float = Field(default=0, ge=-1, le=1, description="情感得分")
    heat_per_minute: float = Field(default=0, ge=0, description="每分钟弹幕数")
    top_positive_phrases: list[str] = Field(default_factory=list, description="高频正向短语")
    top_negative_phrases: list[str] = Field(default_factory=list, description="高频负向短语")
    tags: list[str] = Field(default_factory=list, description="口碑标签")
    summary: str = Field(default="", description="一句话结论")


class PriceTrigger(BaseModel):
    """从口播中识别到的报价触发点。

    Attributes:
        price: 识别到的价格。
        quote: 原始口播片段。
        at_seconds: 出现时间（秒）。
        product_hint: 同一句里出现的商品名提示。
    """

    price: float = Field(..., ge=0, description="识别到的价格")
    quote: str = Field(default="", description="原始口播片段")
    at_seconds: float | None = Field(default=None, ge=0, description="出现时间（秒）")
    product_hint: str | None = Field(default=None, description="商品名提示")


class LivePriceAlert(BaseModel):
    """主播报价触发的一键比价结果。

    Attributes:
        trigger: 触发报价。
        comparison: 全网比价与历史曲线。
        advice: 是否值得当下单。
        is_mock: 是否基于模拟数据。
    """

    trigger: PriceTrigger = Field(..., description="触发报价")
    comparison: PriceComparison = Field(..., description="比价结果")
    advice: str = Field(default="", description="购买建议")
    is_mock: bool = Field(default=False, description="是否基于模拟数据")


class LiveSnapshot(BaseModel):
    """直播会话的实时快照。

    Attributes:
        session_id: 会话标识。
        room_id: 直播间标识。
        title: 直播标题。
        status: 状态（running/ended）。
        key_points: 已提取的关键信息。
        sentiment: 弹幕情感分析。
        price_alert: 最近一次报价比价。
        summary: 当前全场摘要。
        processed_segments: 已处理字幕条数。
        processed_danmaku: 已处理弹幕条数。
        updated_at: 更新时间。
    """

    session_id: str = Field(..., description="会话标识")
    room_id: str = Field(..., description="直播间标识")
    title: str = Field(default="", description="直播标题")
    status: str = Field(default="running", description="状态")
    key_points: list[LiveKeyPoint] = Field(default_factory=list, description="关键信息")
    sentiment: SentimentBreakdown = Field(
        default_factory=SentimentBreakdown, description="弹幕情感"
    )
    price_alert: LivePriceAlert | None = Field(default=None, description="最近一次比价")
    summary: str = Field(default="", description="全场摘要")
    processed_segments: int = Field(default=0, ge=0, description="已处理字幕条数")
    processed_danmaku: int = Field(default=0, ge=0, description="已处理弹幕条数")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class LiveIngestRequest(BaseModel):
    """推入直播事件流。

    Attributes:
        segments: 新增字幕片段。
        danmaku: 新增弹幕。
        current_product: 当前讲解商品标题（用于比价检索）。
    """

    segments: list[TranscriptSegment] = Field(default_factory=list, description="新增字幕")
    danmaku: list[DanmakuItem] = Field(default_factory=list, description="新增弹幕")
    current_product: str | None = Field(default=None, description="当前讲解商品")
