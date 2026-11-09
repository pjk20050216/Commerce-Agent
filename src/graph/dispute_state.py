"""
售后纠纷仲裁庭工作流状态。

Description:
    三个 Agent 严格串行：事实还原 → 规则解读 → 话术生成。
    下游依赖上游产出，因此这里不需要并行分支。
2026-11-09
"""

from operator import add
from typing import Annotated

from pydantic import BaseModel, Field

from src.models.dispute import (
    ArbitrationVerdict,
    ChatMessageInput,
    ComplaintDraft,
    DisputeOrderInput,
    FactSheet,
    LogisticsEventInput,
    UnboxingEvidence,
)


class DisputeState(BaseModel):
    """仲裁庭共享状态。

    Attributes:
        tenant_id: 租户 ID。
        case_id: 案件编号。
        order: 争议订单。
        chat_log: 聊天记录。
        logistics: 物流轨迹。
        unboxing: 开箱凭证。
        claim_text: 用户诉求原文。
        facts: 事实标记（事实还原产出，供规则匹配使用）。
        fact_sheet: 事实还原结果。
        verdict: 裁决结果。
        drafts: 话术草稿（累加）。
        error: 错误信息。
        current_step: 当前步骤。
    """

    tenant_id: str = Field(default="", description="租户 ID")
    case_id: str = Field(default="", description="案件编号")
    order: DisputeOrderInput = Field(..., description="争议订单")
    chat_log: list[ChatMessageInput] = Field(default_factory=list, description="聊天记录")
    logistics: list[LogisticsEventInput] = Field(default_factory=list, description="物流轨迹")
    unboxing: list[UnboxingEvidence] = Field(default_factory=list, description="开箱凭证")
    claim_text: str = Field(default="", description="用户诉求")

    facts: dict[str, bool] = Field(default_factory=dict, description="事实标记")
    fact_sheet: FactSheet | None = Field(default=None, description="事实还原结果")
    verdict: ArbitrationVerdict | None = Field(default=None, description="裁决")
    drafts: Annotated[list[ComplaintDraft], add] = Field(
        default_factory=list, description="话术草稿"
    )
    error: str | None = Field(default=None, description="错误信息")
    current_step: str = Field(default="", description="当前步骤")
