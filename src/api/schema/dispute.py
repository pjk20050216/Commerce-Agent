"""
售后纠纷仲裁庭 API Schema。

Description:
    定义仲裁案件的请求/响应 DTO。2026-11-09
"""

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.dispute import (
    ChatMessageInput,
    DisputeOrderInput,
    DraftTone,
    LogisticsEventInput,
    Responsibility,
    UnboxingEvidence,
)


class DisputeCaseRequest(BaseModel):
    """提交纠纷仲裁的请求。"""

    order: DisputeOrderInput = Field(..., description="争议订单")
    claim_text: str = Field(default="", max_length=2000, description="用户诉求原文")
    chat_log: list[ChatMessageInput] = Field(default_factory=list, description="聊天记录")
    logistics: list[LogisticsEventInput] = Field(default_factory=list, description="物流轨迹")
    unboxing: list[UnboxingEvidence] = Field(default_factory=list, description="开箱凭证")
    persist: bool = Field(default=True, description="是否落库保存")


class DisputeCaseSummary(BaseModel):
    """案件列表项。"""

    case_id: str = Field(..., description="案件编号")
    order_id: str = Field(..., description="订单号")
    platform: str = Field(default="unknown", description="平台")
    responsibility: Responsibility = Field(..., description="责任方")
    confidence: float = Field(default=0.0, description="判定置信度")
    created_at: datetime | None = Field(default=None, description="创建时间")


class RegenerateDraftRequest(BaseModel):
    """重新生成指定语气的话术。"""

    tone: DraftTone = Field(..., description="语气类型")
