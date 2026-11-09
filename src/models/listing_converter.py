"""
视觉商品到刊登商品的转换器。

Description:
    将视觉生成工作流使用的 Product 模型转换为刊登工作流使用的
    ListingProduct 模型，打通两条工作流之间的数据衔接。2026-09-18
"""

import uuid

from src.models.listing import ListingProduct
from src.models.product import Product


def product_to_listing(product: Product) -> ListingProduct:
    """将 Product 转换为 ListingProduct。

    图片不在此处搬运——由 AssetLoaderAgent 在后续阶段从视觉产物中填充，
    因此转换结果的 source_images 始终为空列表。

    Args:
        product: 视觉生成用的商品信息。

    Returns:
        面向刊登的商品信息。

    Example:
        >>> p = Product(name="智能手表", category=ProductCategory.DIGITAL, description="描述")
        >>> listing = product_to_listing(p)
        >>> listing.sku.startswith("VIS-")
        True
    """
    attributes: dict[str, str] = {}
    if product.product_id:
        attributes["source_product_id"] = product.product_id

    if product.product_id:
        sku = product.product_id
    else:
        sku = f"VIS-{uuid.uuid4().hex[:12]}"

    return ListingProduct(
        sku=sku,
        title=product.name,
        description=product.description,
        category=product.category.value,
        brand=product.brand,
        source_images=[],
        attributes=attributes,
    )
