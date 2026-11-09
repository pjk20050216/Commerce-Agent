"""
虚拟买手团工作流状态。

Description:
    买手团采用「三路并行取数 → 汇总决策」的结构：
    风格顾问、性价比分析师、质检员三者互不依赖，可并行执行，
    最后由决策官合并为一张买手决策卡。
2026-11-09
"""

from operator import add
from typing import Annotated

from pydantic import BaseModel, Field

from src.models.buyer import (
    AgentTraceItem,
    BrowsingRecord,
    BuyerDecisionCard,
    CandidateProduct,
    PriceComparison,
    QualityAssessment,
    StyleProfile,
)


class BuyerState(BaseModel):
    """虚拟买手团共享状态。

    Attributes:
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        candidate: 候选商品。
        history: 用户历史行为。
        style_profile: 风格画像（风格顾问产出）。
        style_fit: 候选商品与画像的匹配分 0-100。
        style_reasons: 匹配分依据。
        price_comparison: 全网比价（性价比分析师产出）。
        quality: 质量口碑评估（质检员产出）。
        card: 最终决策卡（决策官产出）。
        agent_trace: 各 Agent 执行痕迹（累加）。
        error: 错误信息。
        current_step: 当前步骤。
    """

    tenant_id: str = Field(default="", description="租户 ID")
    user_id: str = Field(default="", description="用户 ID")
    candidate: CandidateProduct = Field(..., description="候选商品")
    history: list[BrowsingRecord] = Field(default_factory=list, description="历史行为")

    style_profile: StyleProfile | None = Field(default=None, description="风格画像")
    style_fit: float | None = Field(default=None, description="风格匹配分")
    style_reasons: list[str] = Field(default_factory=list, description="匹配依据")
    price_comparison: PriceComparison | None = Field(default=None, description="全网比价")
    quality: QualityAssessment | None = Field(default=None, description="质量评估")

    card: BuyerDecisionCard | None = Field(default=None, description="决策卡")
    agent_trace: Annotated[list[AgentTraceItem], add] = Field(
        default_factory=list, description="Agent 执行痕迹"
    )
    error: str | None = Field(default=None, description="错误信息")
    current_step: str = Field(default="", description="当前步骤")
