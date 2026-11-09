"""
创意方案模型模块。

Description:
    定义创意策划阶段的数据模型，包括视觉风格、配色方案、
    图片提示词以及完整的创意方案。2026-09-02
"""

from enum import Enum

from pydantic import BaseModel, Field


class VisualStyle(str, Enum):
    """视觉风格枚举。

    Attributes:
        MODERN: 现代简约。
        LUXURY: 轻奢高端。
        MINIMAL: 极简风。
        VINTAGE: 复古风。
        TECH: 科技感。
        NATURAL: 自然清新。
        CUTE: 可爱亲和。
        SPORTY: 运动活力。
    """

    MODERN = "modern"
    LUXURY = "luxury"
    MINIMAL = "minimal"
    VINTAGE = "vintage"
    TECH = "tech"
    NATURAL = "natural"
    CUTE = "cute"
    SPORTY = "sporty"


class ImageType(str, Enum):
    """图片类型枚举。

    Attributes:
        MAIN: 主图。
        SCENE: 场景图。
        SELLING_POINT: 卖点图。
    """

    MAIN = "main"
    SCENE = "scene"
    SELLING_POINT = "selling_point"


class ColorRole(str, Enum):
    """配色角色枚举。

    Attributes:
        PRIMARY: 主色。
        SECONDARY: 辅色。
        ACCENT: 强调色。
        BACKGROUND: 背景色。
        TEXT: 文字色。
    """

    PRIMARY = "primary"
    SECONDARY = "secondary"
    ACCENT = "accent"
    BACKGROUND = "background"
    TEXT = "text"


class ColorInfo(BaseModel):
    """单色信息。

    Attributes:
        name: 颜色名称。
        hex: 十六进制色值，如 "#FF5733"。
        role: 配色角色。
    """

    name: str = Field(..., description="颜色名称")
    hex: str = Field(..., description="十六进制色值，如 #FF5733")
    role: ColorRole = Field(default=ColorRole.PRIMARY, description="配色角色")


class ColorPalette(BaseModel):
    """配色方案。

    Attributes:
        name: 方案名称。
        colors: 颜色列表。
        mood: 情绪基调描述。
        description: 方案说明。
    """

    name: str = Field(..., description="方案名称")
    colors: list[ColorInfo] = Field(default_factory=list, description="颜色列表")
    mood: str | None = Field(default=None, description="情绪基调")
    description: str | None = Field(default=None, description="方案说明")

    def get_color(self, role: ColorRole) -> ColorInfo | None:
        """按角色查找颜色。

        Args:
            role: 配色角色。

        Returns:
            匹配的颜色信息，未找到时返回 None。
        """
        for color in self.colors:
            if color.role == role:
                return color
        return None


class CreativePlan(BaseModel):
    """创意方案。

    Attributes:
        name: 方案名称。
        visual_style: 视觉风格。
        color_palette: 配色方案。
        key_elements: 关键视觉元素。
        style_keywords: 风格关键词。
        target_emotion: 目标情绪。
        description: 方案描述。
    """

    name: str = Field(..., description="方案名称")
    visual_style: VisualStyle = Field(
        default=VisualStyle.MODERN, description="视觉风格"
    )
    color_palette: ColorPalette | None = Field(default=None, description="配色方案")
    key_elements: list[str] = Field(default_factory=list, description="关键视觉元素")
    style_keywords: list[str] = Field(default_factory=list, description="风格关键词")
    target_emotion: str | None = Field(default=None, description="目标情绪")
    description: str | None = Field(default=None, description="方案描述")


class ImagePrompt(BaseModel):
    """图片生成提示词。

    Attributes:
        prompt: 正向提示词。
        negative_prompt: 反向提示词。
        image_type: 图片类型。
        aspect_ratio: 宽高比，如 "1:1"。
        style_keywords: 风格关键词。
    """

    prompt: str = Field(..., description="正向提示词")
    negative_prompt: str | None = Field(default=None, description="反向提示词")
    image_type: ImageType = Field(default=ImageType.MAIN, description="图片类型")
    aspect_ratio: str = Field(default="1:1", description="宽高比")
    style_keywords: list[str] = Field(default_factory=list, description="风格关键词")
