"""
直播购物分身 API Schema。

Description:
    定义直播会话管理的请求/响应 DTO。2026-11-09
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateLiveSessionRequest(BaseModel):
    """创建直播会话的请求。"""

    room_id: str = Field(..., min_length=1, max_length=100, description="直播间标识")
    title: str = Field(default="", max_length=200, description="直播标题")
    platform: str = Field(default="", max_length=50, description="直播平台")


class LiveSessionSummary(BaseModel):
    """直播会话列表项。"""

    session_id: str = Field(..., description="会话标识")
    room_id: str = Field(default="", description="直播间标识")
    title: str = Field(default="", description="直播标题")
    status: str = Field(default="running", description="状态")
    updated_at: datetime | None = Field(default=None, description="更新时间")


class LivePriceCheckRequest(BaseModel):
    """独立一键比价请求。"""

    title: str = Field(..., min_length=1, max_length=300, description="商品标题")
    price: float = Field(..., gt=0, description="主播报价")
