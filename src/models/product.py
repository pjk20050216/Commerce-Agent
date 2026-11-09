"""
商品信息模型模块。

Description:
    定义电商购物商品的核心数据模型，包括商品基本信息、类目枚举、
    卖点以及规格参数。作为整个工作流的输入数据源。2026-09-02
"""

from enum import Enum

from pydantic import BaseModel, Field


class ProductCategory(str, Enum):
    """商品类目枚举。

    Attributes:
        DIGITAL: 数码电子。
        BEAUTY: 美妆个护。
        APPAREL: 服饰鞋包。
        HOME: 家居生活。
        SPORTS: 运动户外。
        FOOD: 食品饮料。
        TOYS: 玩具母婴。
        AUTOMOTIVE: 汽车用品。
        PET: 宠物用品。
        OTHER: 其他。
    """

    DIGITAL = "digital"
    BEAUTY = "beauty"
    APPAREL = "apparel"
    HOME = "home"
    SPORTS = "sports"
    FOOD = "food"
    TOYS = "toys"
    AUTOMOTIVE = "automotive"
    PET = "pet"
    OTHER = "other"


class SellingPointType(str, Enum):
    """卖点类型枚举。

    Attributes:
        FUNCTIONAL: 功能特性。
        EMOTIONAL: 情感价值。
        SOCIAL: 社交属性。
        PRICE: 价格优势。
        QUALITY: 品质保障。
        SERVICE: 服务保障。
    """

    FUNCTIONAL = "functional"
    EMOTIONAL = "emotional"
    SOCIAL = "social"
    PRICE = "price"
    QUALITY = "quality"
    SERVICE = "service"


class ProductSpec(BaseModel):
    """商品规格参数。

    Attributes:
        name: 规格名称，如"重量"。
        value: 规格值，如"150"。
        unit: 计量单位，如"g"，可为空。

    Example:
        >>> spec = ProductSpec(name="重量", value="150", unit="g")
        >>> assert spec.name == "重量"
    """

    name: str = Field(..., description="规格名称")
    value: str = Field(..., description="规格值")
    unit: str | None = Field(default=None, description="计量单位")


class SellingPoint(BaseModel):
    """商品卖点。

    Attributes:
        title: 卖点标题。
        description: 卖点详细描述。
        point_type: 卖点类型，默认 FUNCTIONAL。
        priority: 优先级，数值越大越重要，默认 1。
        keywords: 关联关键词列表。

    Example:
        >>> point = SellingPoint(title="超长续航", description="续航长达 7 天")
        >>> assert point.priority == 1
    """

    title: str = Field(..., description="卖点标题")
    description: str = Field(..., description="卖点详细描述")
    point_type: SellingPointType = Field(
        default=SellingPointType.FUNCTIONAL, description="卖点类型"
    )
    priority: int = Field(default=1, ge=0, le=10, description="优先级，数值越大越重要")
    keywords: list[str] = Field(default_factory=list, description="关联关键词")


class Product(BaseModel):
    """商品信息。

    作为视觉生成与刊登工作流的输入数据。

    Attributes:
        product_id: 商品唯一标识，未提供时自动生成。
        name: 商品名称。
        brand: 品牌名称。
        category: 商品类目。
        description: 商品描述。
        selling_points: 卖点列表。
        specifications: 规格参数列表。
        tags: 标签列表。
        target_audience: 目标受众描述。
        style_preference: 风格偏好描述。

    Example:
        >>> product = Product(
        ...     name="智能手表",
        ...     category=ProductCategory.DIGITAL,
        ...     description="支持健康监测的运动手表",
        ... )
        >>> assert product.name == "智能手表"
    """

    product_id: str | None = Field(default=None, description="商品唯一标识")
    name: str = Field(..., description="商品名称")
    brand: str | None = Field(default=None, description="品牌名称")
    category: ProductCategory = Field(
        default=ProductCategory.OTHER, description="商品类目"
    )
    description: str = Field(..., description="商品描述")
    selling_points: list[SellingPoint] = Field(
        default_factory=list, description="卖点列表"
    )
    specifications: list[ProductSpec] = Field(
        default_factory=list, description="规格参数列表"
    )
    tags: list[str] = Field(default_factory=list, description="标签列表")
    target_audience: str | None = Field(default=None, description="目标受众")
    style_preference: str | None = Field(default=None, description="风格偏好")

    def get_main_selling_points(self, limit: int = 3) -> list[SellingPoint]:
        """获取优先级最高的卖点。

        Args:
            limit: 返回的卖点数量上限。

        Returns:
            按优先级降序排列的卖点列表。

        Example:
            >>> product.get_main_selling_points(limit=2)  # doctest: +SKIP
        """
        return sorted(self.selling_points, key=lambda p: p.priority, reverse=True)[:limit]

    def get_keywords(self) -> list[str]:
        """汇总商品标签与卖点关键词。

        Returns:
            去重后的关键词列表，保持首次出现顺序。

        Example:
            >>> Product(name="A", description="B", tags=["智能"]).get_keywords()
            ['智能']
        """
        keywords: list[str] = []
        for tag in self.tags:
            if tag not in keywords:
                keywords.append(tag)
        for point in self.selling_points:
            for kw in point.keywords:
                if kw not in keywords:
                    keywords.append(kw)
        return keywords
