"""
分镜脚本模型模块。

Description:
    定义视频分镜阶段的数据模型，包括场景类型、镜头景别、
    转场方式以及完整的分镜脚本。2026-09-02
"""

from enum import Enum

from pydantic import BaseModel, Field


class SceneType(str, Enum):
    """场景类型枚举。

    Attributes:
        PRODUCT_INTRO: 产品介绍。
        FEATURE_HIGHLIGHT: 功能卖点展示。
        USAGE_SCENARIO: 使用场景演示。
        BRAND_MOMENT: 品牌时刻。
        CALL_TO_ACTION: 行动号召。
    """

    PRODUCT_INTRO = "product_intro"
    FEATURE_HIGHLIGHT = "feature_highlight"
    USAGE_SCENARIO = "usage_scenario"
    BRAND_MOMENT = "brand_moment"
    CALL_TO_ACTION = "call_to_action"


class ShotType(str, Enum):
    """镜头景别枚举。

    Attributes:
        WIDE: 远景/全景。
        MEDIUM: 中景。
        CLOSE_UP: 特写。
    """

    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"


class TransitionType(str, Enum):
    """转场方式枚举。

    Attributes:
        CUT: 硬切。
        FADE: 淡入淡出。
        DISSOLVE: 叠化。
    """

    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"


class Scene(BaseModel):
    """分镜场景。

    Attributes:
        scene_id: 场景序号。
        scene_type: 场景类型。
        duration: 场景时长（秒）。
        shot_type: 镜头景别。
        transition_in: 入场转场方式。
        transition_out: 出场转场方式。
        description: 场景画面描述。
        visual_prompt: 视觉提示词。
    """

    scene_id: int = Field(..., description="场景序号")
    scene_type: SceneType = Field(
        default=SceneType.PRODUCT_INTRO, description="场景类型"
    )
    duration: float = Field(default=5.0, gt=0, description="场景时长（秒）")
    shot_type: ShotType = Field(default=ShotType.MEDIUM, description="镜头景别")
    transition_in: TransitionType = Field(
        default=TransitionType.CUT, description="入场转场方式"
    )
    transition_out: TransitionType = Field(
        default=TransitionType.CUT, description="出场转场方式"
    )
    description: str = Field(..., description="场景画面描述")
    visual_prompt: str = Field(..., description="视觉提示词")


class Storyboard(BaseModel):
    """分镜脚本。

    Attributes:
        storyboard_id: 分镜唯一标识。
        title: 分镜标题。
        description: 分镜说明。
        scenes: 场景列表。
        total_duration: 总时长（秒）。
        resolution: 分辨率，如 "1080p"。
        visual_style: 视觉风格描述。
    """

    storyboard_id: str | None = Field(default=None, description="分镜唯一标识")
    title: str = Field(..., description="分镜标题")
    description: str | None = Field(default=None, description="分镜说明")
    scenes: list[Scene] = Field(default_factory=list, description="场景列表")
    total_duration: float = Field(default=0.0, description="总时长（秒）")
    resolution: str = Field(default="1080p", description="分辨率")
    visual_style: str | None = Field(default=None, description="视觉风格")

    def computed_duration(self) -> float:
        """按场景时长累加计算总时长。

        Returns:
            所有场景时长之和（秒）。
        """
        return sum(scene.duration for scene in self.scenes)
