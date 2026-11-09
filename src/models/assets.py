"""
生成资产模型模块。

Description:
    定义图片、视频等生成产物的数据模型，以及资产状态、格式枚举
    和质量审核相关的模型。2026-09-02
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AssetStatus(str, Enum):
    """资产状态枚举。

    Attributes:
        PENDING: 排队中。
        PROCESSING: 生成中。
        COMPLETED: 已完成。
        FAILED: 失败。
        CANCELLED: 已取消。
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageFormat(str, Enum):
    """图片格式枚举。

    Attributes:
        PNG: PNG 格式。
        JPG: JPG 格式。
        WEBP: WebP 格式。
    """

    PNG = "png"
    JPG = "jpg"
    WEBP = "webp"


class VideoFormat(str, Enum):
    """视频格式枚举。

    Attributes:
        MP4: MP4 格式。
        MOV: MOV 格式。
        WEBM: WebM 格式。
    """

    MP4 = "mp4"
    MOV = "mov"
    WEBM = "webm"


class GeneratedImage(BaseModel):
    """生成的图片。

    Attributes:
        image_id: 图片唯一标识。
        image_type: 图片类型（main/scene/selling_point）。
        prompt: 使用的正向提示词。
        negative_prompt: 使用的反向提示词。
        url: 图片访问地址。
        local_path: 本地存储路径。
        model: 生成模型名称。
        format: 图片格式。
        width: 宽度（像素）。
        height: 高度（像素）。
        file_size: 文件大小（字节）。
        status: 生成状态。
        metadata: 附加元数据。
    """

    image_id: str = Field(..., description="图片唯一标识")
    image_type: str = Field(default="main", description="图片类型")
    prompt: str | None = Field(default=None, description="正向提示词")
    negative_prompt: str | None = Field(default=None, description="反向提示词")
    url: str | None = Field(default=None, description="图片访问地址")
    local_path: str | None = Field(default=None, description="本地存储路径")
    model: str | None = Field(default=None, description="生成模型名称")
    format: ImageFormat = Field(default=ImageFormat.PNG, description="图片格式")
    width: int | None = Field(default=None, description="宽度（像素）")
    height: int | None = Field(default=None, description="高度（像素）")
    file_size: int | None = Field(default=None, description="文件大小（字节）")
    status: AssetStatus = Field(default=AssetStatus.PENDING, description="生成状态")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    def is_ready(self) -> bool:
        """判断图片是否可用于后续处理。

        Returns:
            当状态为 COMPLETED 且存在 url 或 local_path 时返回 True。

        Example:
            >>> GeneratedImage(image_id="1", url="x").is_ready()
            False
        """
        if self.status != AssetStatus.COMPLETED:
            return False
        return bool(self.url or self.local_path)


class GeneratedVideo(BaseModel):
    """生成的视频。

    Attributes:
        video_id: 视频唯一标识。
        title: 视频标题。
        visual_prompt: 使用的视觉提示词。
        url: 视频访问地址。
        local_path: 本地存储路径。
        model: 生成模型名称。
        format: 视频格式。
        duration: 时长（秒）。
        width: 宽度（像素）。
        height: 高度（像素）。
        fps: 帧率。
        file_size: 文件大小（字节）。
        progress: 生成进度（0-100）。
        storyboard_id: 关联的分镜标识。
        status: 生成状态。
        metadata: 附加元数据。
    """

    video_id: str = Field(..., description="视频唯一标识")
    title: str | None = Field(default=None, description="视频标题")
    visual_prompt: str | None = Field(default=None, description="视觉提示词")
    url: str | None = Field(default=None, description="视频访问地址")
    local_path: str | None = Field(default=None, description="本地存储路径")
    model: str | None = Field(default=None, description="生成模型名称")
    format: VideoFormat = Field(default=VideoFormat.MP4, description="视频格式")
    duration: float | None = Field(default=None, description="时长（秒）")
    width: int | None = Field(default=None, description="宽度（像素）")
    height: int | None = Field(default=None, description="高度（像素）")
    fps: int | None = Field(default=None, description="帧率")
    file_size: int | None = Field(default=None, description="文件大小（字节）")
    progress: int = Field(default=0, ge=0, le=100, description="生成进度")
    storyboard_id: str | None = Field(default=None, description="关联的分镜标识")
    status: AssetStatus = Field(default=AssetStatus.PENDING, description="生成状态")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    def is_ready(self) -> bool:
        """判断视频是否可用于后续处理。

        Returns:
            当状态为 COMPLETED 且存在 url 或 local_path 时返回 True。
        """
        if self.status != AssetStatus.COMPLETED:
            return False
        return bool(self.url or self.local_path)


class QualityScore(BaseModel):
    """质量评分。

    Attributes:
        overall_score: 总体评分（0-1）。
        clarity_score: 清晰度评分（0-1）。
        composition_score: 构图评分（0-1）。
        color_score: 色彩评分（0-1）。
        relevance_score: 相关性评分（0-1）。
    """

    overall_score: float = Field(default=0.0, ge=0, le=1, description="总体评分")
    clarity_score: float = Field(default=0.8, ge=0, le=1, description="清晰度评分")
    composition_score: float = Field(default=0.8, ge=0, le=1, description="构图评分")
    color_score: float = Field(default=0.8, ge=0, le=1, description="色彩评分")
    relevance_score: float = Field(default=0.8, ge=0, le=1, description="相关性评分")


class QualityIssue(BaseModel):
    """质量问题。

    Attributes:
        issue_type: 问题类型。
        severity: 严重程度（info/warning/error）。
        description: 问题描述。
        suggestion: 改进建议。
    """

    issue_type: str = Field(..., description="问题类型")
    description: str = Field(..., description="问题描述")
    severity: str = Field(default="warning", description="严重程度")
    suggestion: str | None = Field(default=None, description="改进建议")


class QualityReport(BaseModel):
    """质量审核报告。

    Attributes:
        asset_id: 被审核资产的标识。
        asset_type: 资产类型（image/video）。
        score: 质量评分。
        passed: 是否通过审核。
        issues: 问题列表。
    """

    asset_id: str = Field(..., description="被审核资产的标识")
    asset_type: str = Field(default="image", description="资产类型")
    score: QualityScore = Field(default_factory=QualityScore, description="质量评分")
    passed: bool = Field(default=True, description="是否通过审核")
    issues: list[QualityIssue] = Field(default_factory=list, description="问题列表")


class AssetCollection(BaseModel):
    """资产合集。

    Attributes:
        collection_id: 合集唯一标识。
        task_id: 关联任务标识。
        product_name: 商品名称。
        images: 生成图片列表。
        videos: 生成视频列表。
        quality_reports: 质量报告列表。
    """

    collection_id: str = Field(..., description="合集唯一标识")
    task_id: str = Field(..., description="关联任务标识")
    product_name: str | None = Field(default=None, description="商品名称")
    images: list[GeneratedImage] = Field(default_factory=list, description="图片列表")
    videos: list[GeneratedVideo] = Field(default_factory=list, description="视频列表")
    quality_reports: list[QualityReport] = Field(
        default_factory=list, description="质量报告列表"
    )
