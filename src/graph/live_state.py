"""
直播购物分身工作流状态。

Description:
    每收到一批字幕/弹幕就触发一次「增量快照」计算：
    字幕摘要与弹幕情感互不依赖可并行，比价依赖字幕抽出的报价。
2026-11-09
"""

from pydantic import BaseModel, Field

from src.models.live import (
    DanmakuItem,
    LiveKeyPoint,
    LivePriceAlert,
    LiveSnapshot,
    SentimentBreakdown,
    TranscriptSegment,
)


class LiveState(BaseModel):
    """单批次直播处理状态。

    Attributes:
        session_id: 会话标识。
        room_id: 直播间标识。
        title: 直播标题。
        tenant_id: 租户 ID。
        snapshot: 上一版快照（用于增量合并）。
        segments: 本批新增字幕。
        danmaku: 本批新增弹幕。
        current_product: 当前讲解商品。
        key_points: 本批新增关键信息。
        sentiment: 本批弹幕情感。
        price_alert: 本批比价结果。
        result: 合并后的新快照。
        error: 错误信息。
        current_step: 当前步骤。
    """

    session_id: str = Field(..., description="会话标识")
    room_id: str = Field(default="", description="直播间标识")
    title: str = Field(default="", description="直播标题")
    tenant_id: str = Field(default="", description="租户 ID")
    snapshot: LiveSnapshot | None = Field(default=None, description="上一版快照")
    segments: list[TranscriptSegment] = Field(default_factory=list, description="新增字幕")
    danmaku: list[DanmakuItem] = Field(default_factory=list, description="新增弹幕")
    current_product: str | None = Field(default=None, description="当前讲解商品")

    key_points: list[LiveKeyPoint] = Field(default_factory=list, description="本批关键信息")
    sentiment: SentimentBreakdown | None = Field(default=None, description="本批弹幕情感")
    price_alert: LivePriceAlert | None = Field(default=None, description="本批比价")
    result: LiveSnapshot | None = Field(default=None, description="合并后的快照")
    error: str | None = Field(default=None, description="错误信息")
    current_step: str = Field(default="", description="当前步骤")
