"""
刊登工具数据模型模块。

Description:
    定义多平台刊登流程的数据模型，包括目标平台、商品信息、图片引用、
    素材包、文案包、合规报告以及刊登任务状态。2026-09-18
"""

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Platform(str, Enum):
    """目标电商平台枚举。

    值统一为平台基础标识，Amazon 分站点共享同一套适配器与规则。

    Attributes:
        AMAZON: Amazon（通用）。
        AMAZON_US: Amazon 美国站。
        AMAZON_UK: Amazon 英国站。
        AMAZON_JP: Amazon 日本站。
        AMAZON_DE: Amazon 德国站。
        EBAY: eBay。
        SHOPIFY: Shopify。
    """

    AMAZON = "amazon"
    AMAZON_US = "amazon_us"
    AMAZON_UK = "amazon_uk"
    AMAZON_JP = "amazon_jp"
    AMAZON_DE = "amazon_de"
    EBAY = "ebay"
    SHOPIFY = "shopify"

    @property
    def base(self) -> str:
        """获取平台基础标识（去除分站点后缀）。

        Returns:
            平台基础标识，如 amazon_us 返回 amazon。

        Example:
            >>> Platform.AMAZON_UK.base
            'amazon'
        """
        return self.value.split("_")[0]


class TaskStatus(str, Enum):
    """刊登任务状态枚举。

    Attributes:
        PENDING: 待处理。
        GENERATING: 素材/文案生成中。
        CHECKING: 合规检查中。
        PUSHING: 推送平台中。
        COMPLETED: 已完成。
        FAILED: 失败。
    """

    PENDING = "pending"
    GENERATING = "generating"
    CHECKING = "checking"
    PUSHING = "pushing"
    COMPLETED = "completed"
    FAILED = "failed"


class ComplianceStatus(str, Enum):
    """合规状态枚举。

    Attributes:
        PASS: 通过。
        WARNING: 警告。
        FAIL: 不通过。
    """

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class ImageRef(BaseModel):
    """图片引用。

    Attributes:
        url: 图片地址。
        is_main: 是否为主图。
        width: 宽度（像素）。
        height: 高度（像素）。
        file_size: 文件大小（字节）。
    """

    url: str = Field(..., description="图片地址")
    is_main: bool = Field(default=False, description="是否为主图")
    width: int | None = Field(default=None, description="宽度（像素）")
    height: int | None = Field(default=None, description="高度（像素）")
    file_size: int | None = Field(default=None, description="文件大小（字节）")


class ListingProduct(BaseModel):
    """面向刊登的商品信息。

    Attributes:
        sku: 商品唯一编码。
        title: 商品标题。
        description: 商品描述。
        category: 商品类目。
        brand: 品牌。
        price: 价格。
        weight: 重量（千克）。
        dimensions: 尺寸信息。
        source_images: 原始图片列表。
        attributes: 附加属性。
    """

    sku: str = Field(..., description="商品唯一编码")
    title: str = Field(..., description="商品标题")
    description: str | None = Field(default=None, description="商品描述")
    category: str | None = Field(default=None, description="商品类目")
    brand: str | None = Field(default=None, description="品牌")
    price: Decimal | None = Field(default=None, description="价格")
    weight: Decimal | None = Field(default=None, description="重量（千克）")
    dimensions: dict[str, Any] | None = Field(default=None, description="尺寸信息")
    source_images: list[ImageRef] = Field(default_factory=list, description="原始图片")
    attributes: dict[str, Any] = Field(default_factory=dict, description="附加属性")

    @property
    def main_image(self) -> ImageRef | None:
        """获取主图。

        Returns:
            标记为主图的图片，不存在时返回 None。

        Example:
            >>> ListingProduct(sku="A", title="B").main_image is None
            True
        """
        for image in self.source_images:
            if image.is_main:
                return image
        return None


class AssetPackage(BaseModel):
    """平台素材包。

    Attributes:
        listing_task_id: 关联刊登任务 ID。
        platform: 目标平台。
        main_image: 主图地址。
        variant_images: 附加图地址列表。
        video_url: 视频地址。
    """

    listing_task_id: int = Field(..., description="关联刊登任务 ID")
    platform: Platform = Field(..., description="目标平台")
    main_image: str | None = Field(default=None, description="主图地址")
    variant_images: list[str] = Field(default_factory=list, description="附加图列表")
    video_url: str | None = Field(default=None, description="视频地址")


class CopywritingPackage(BaseModel):
    """平台文案包。

    Attributes:
        listing_task_id: 关联刊登任务 ID。
        platform: 目标平台。
        language: 文案语种。
        title: 优化后标题。
        bullet_points: 卖点条目。
        description: 商品描述。
        search_terms: 搜索关键词。
    """

    listing_task_id: int = Field(..., description="关联刊登任务 ID")
    platform: Platform = Field(..., description="目标平台")
    language: str = Field(default="en", description="文案语种")
    title: str = Field(..., description="优化后标题")
    bullet_points: list[str] = Field(default_factory=list, description="卖点条目")
    description: str = Field(default="", description="商品描述")
    search_terms: list[str] = Field(default_factory=list, description="搜索关键词")


class ComplianceIssue(BaseModel):
    """合规问题。

    Attributes:
        rule: 规则编号。
        field: 问题字段。
        message: 问题描述。
        severity: 严重程度。
        suggestion: 改进建议。
    """

    rule: str = Field(..., description="规则编号")
    field: str = Field(..., description="问题字段")
    message: str = Field(..., description="问题描述")
    severity: ComplianceStatus = Field(
        default=ComplianceStatus.FAIL, description="严重程度"
    )
    suggestion: str | None = Field(default=None, description="改进建议")


class ComplianceReport(BaseModel):
    """平台合规报告。

    Attributes:
        id: 报告标识。
        listing_task_id: 关联刊登任务 ID。
        platform: 目标平台。
        overall: 总体结论。
        image_issues: 图片类问题。
        text_issues: 文案类问题。
    """

    id: int | None = Field(default=None, description="报告标识")
    listing_task_id: int = Field(..., description="关联刊登任务 ID")
    platform: Platform = Field(..., description="目标平台")
    overall: ComplianceStatus = Field(
        default=ComplianceStatus.PASS, description="总体结论"
    )
    image_issues: list[ComplianceIssue] = Field(
        default_factory=list, description="图片类问题"
    )
    text_issues: list[ComplianceIssue] = Field(
        default_factory=list, description="文案类问题"
    )
    forbidden_words: list[str] = Field(
        default_factory=list, description="命中的禁词列表"
    )

    @property
    def is_pass(self) -> bool:
        """是否整体通过。

        Returns:
            overall 为 PASS 时返回 True。
        """
        return self.overall == ComplianceStatus.PASS

    @property
    def issues(self) -> list[ComplianceIssue]:
        """全部问题列表。

        Returns:
            图片类与文案类问题的合并列表。
        """
        return [*self.image_issues, *self.text_issues]

    def mark_fail(self, issue: ComplianceIssue, field: str = "text") -> None:
        """记录一个问题并更新总体结论。

        Args:
            issue: 合规问题。
            field: 问题归属，text 归入文案类，image 归入图片类。

        Example:
            >>> report = ComplianceReport(listing_task_id=1, platform=Platform.AMAZON)
            >>> report.mark_fail(ComplianceIssue(rule="TXT-001", field="title", message="过长"))
            >>> report.is_pass
            False
        """
        if field == "image":
            self.image_issues.append(issue)
        else:
            self.text_issues.append(issue)
        if issue.severity == ComplianceStatus.FAIL:
            self.overall = ComplianceStatus.FAIL
        elif self.overall == ComplianceStatus.PASS:
            self.overall = ComplianceStatus.WARNING


class ListingTask(BaseModel):
    """刊登任务。

    Attributes:
        id: 任务标识。
        product_id: 关联商品 ID。
        target_platforms: 目标平台列表。
        status: 任务状态。

    Example:
        >>> task = ListingTask(product_id=1, target_platforms=[Platform.AMAZON])
        >>> task.status
        <TaskStatus.PENDING: 'pending'>
    """

    model_config = ConfigDict(validate_assignment=True)

    id: int | None = Field(default=None, description="任务标识")
    product_id: int = Field(..., description="关联商品 ID")
    target_platforms: list[Platform] = Field(
        default_factory=list, description="目标平台列表"
    )
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")

    def mark_generating(self) -> None:
        """标记任务进入生成阶段。"""
        self.status = TaskStatus.GENERATING

    def mark_checking(self) -> None:
        """标记任务进入合规检查阶段。"""
        self.status = TaskStatus.CHECKING

    def mark_pushing(self) -> None:
        """标记任务进入推送阶段。"""
        self.status = TaskStatus.PUSHING

    def mark_completed(self) -> None:
        """标记任务完成。"""
        self.status = TaskStatus.COMPLETED

    def mark_failed(self) -> None:
        """标记任务失败。"""
        self.status = TaskStatus.FAILED
