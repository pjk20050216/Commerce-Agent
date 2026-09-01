"""
刊登工作流状态定义。

Description:
    定义刊登工作流的共享状态模型，支持素材和文案的并行生成。2026-09-18
"""

from operator import or_
from typing import Annotated, Any

from pydantic import BaseModel, Field

from src.models.listing import (
    AssetPackage,
    ComplianceReport,
    CopywritingPackage,
    ListingProduct,
    Platform,
)


class ListingState(BaseModel):
    """刊登工作流共享状态。

    状态流转:
        PENDING → 商品导入 → 素材+文案并行生成 → 结果收集

    Attributes:
        product: 待刊登的标准化商品。
        asset_packages: 各平台的素材包 (platform -> package)。
        copywriting_packages: 各平台的文案包 (platform -> package)。
        compliance_reports: 各平台的合规报告 (platform -> report)。
        push_results: 各平台推送结果。
        target_platforms: 目标平台列表。
        error: 错误信息（如有）。
        current_step: 当前执行步骤。
        step_results: 各步骤执行结果。
    """

    product: ListingProduct | None = None
    tenant_id: str = Field(default="", description="租户 ID")
    # Platform-keyed dicts 使用 operator.or_ merge reducer：
    # 并行节点分别返回不同 platform 的结果时，会被合并而非覆盖
    asset_packages: Annotated[dict[Platform, AssetPackage], or_] = Field(default_factory=dict)
    copywriting_packages: Annotated[dict[Platform, CopywritingPackage], or_] = Field(default_factory=dict)
    compliance_reports: Annotated[dict[Platform, ComplianceReport], or_] = Field(default_factory=dict)
    push_results: dict[str, Any] = Field(default_factory=dict, description="各平台推送结果")
    target_platforms: list[Platform] = Field(default_factory=list)
    error: str | None = None
    current_step: str = ""
    # 使用 operator.or_ 合并（dict | dict），确保并行节点写入时不会相互覆盖
    step_results: Annotated[dict[str, Any], or_] = Field(default_factory=dict)
