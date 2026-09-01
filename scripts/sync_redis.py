"""Sync products from PostgreSQL to Redis for API consumption.

The seed_data.py script populated PostgreSQL tables,
but the API reads products from Redis. This script bridges the gap.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Map real Amazon categories to ProductCategory enum values
CATEGORY_MAP = {
    "Electronics": "digital",
    "Cell Phones & Accessories": "digital",
    "Computers & Accessories": "digital",
    "Home & Kitchen": "home",
    "Kitchen & Dining": "home",
    "Home Improvement": "home",
    "Sports & Outdoors": "sports",
    "Sports & Fitness": "sports",
    "Clothing, Shoes & Jewelry": "clothing",
    "Beauty & Personal Care": "beauty",
    "Pet Supplies": "pet",
    "Baby Products": "baby",
    "Grocery & Gourmet Food": "food",
    "Toys & Games": "other",
    "Office Products": "other",
    "Automotive": "other",
    "Tools & Home Improvement": "home",
    "Health & Household": "other",
    "Industrial & Scientific": "other",
    "Musical Instruments": "other",
    "Patio, Lawn & Garden": "home",
}


def map_category(category_name: str) -> str:
    """Map a real Amazon category name to ProductCategory enum value."""
    return CATEGORY_MAP.get(category_name, "other")


def map_selling_points(raw_points: list[dict]) -> list[dict]:
    """Convert seed data selling points to proper SellingPoint format.

    Seed data format: [{"title": "..."}, ...]
    Required format: [{"title": "...", "description": "...", "point_type": "functional", "priority": 3}, ...]
    """
    result = []
    for i, sp in enumerate(raw_points):
        title = sp.get("title", "") if isinstance(sp, dict) else str(sp)
        # Priority: first item gets highest, descending
        priority = max(1, 5 - i)
        result.append({
            "title": title[:50],
            "description": sp.get("description", title)[:500],
            "point_type": "functional",
            "priority": priority,
            "keywords": [],
        })
    return result


def map_specifications(raw_specs: dict | list) -> list[dict]:
    """Convert seed data specifications to list of ProductSpec objects.

    Seed data format: {"key": "value", ...}
    Required format: [{"name": "key", "value": "value", "unit": None}, ...]
    """
    if isinstance(raw_specs, list):
        return raw_specs
    if isinstance(raw_specs, dict):
        return [
            {"name": str(k), "value": str(v), "unit": None}
            for k, v in raw_specs.items()
        ]
    return []


async def main():
    os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
    os.environ.setdefault("POSTGRES_PORT", "5432")
    os.environ.setdefault("POSTGRES_USER", "postgres")
    os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
    os.environ.setdefault("POSTGRES_DB", "cbcf")

    from src.api.service.redis_client import get_redis
    from src.db.postgres import get_db_session
    from src.db.models import Product as ProductPO
    from src.models.product import Product
    from sqlalchemy import select

    redis = await get_redis()
    await redis._ensure_connected()

    tenant_id = "default"
    product_count = 0
    error_count = 0

    async with get_db_session() as session:
        result = await session.execute(
            select(ProductPO).where(ProductPO.tenant_id == tenant_id)
        )
        products = result.scalars().all()

        print(f"Found {len(products)} products in PostgreSQL")

        for po in products:
            # Get raw values with safe defaults
            raw_category = getattr(po, "category", "") or "other"
            raw_selling_points = getattr(po, "selling_points", []) or []
            raw_specs = getattr(po, "specifications", {}) or {}
            raw_description = getattr(po, "description", "") or ""

            try:
                product = Product(
                    product_id=po.product_id,
                    name=getattr(po, "name", "") or "Unknown Product",
                    brand=getattr(po, "brand", "") or "",
                    category=map_category(raw_category),
                    description=raw_description[:2000] if raw_description else "No description available.",
                    selling_points=map_selling_points(raw_selling_points),
                    specifications=map_specifications(raw_specs),
                )
                # Save to BOTH tenant IDs for compatibility
                await redis.save_product(product, tenant_id="default")
                await redis.save_product(product, tenant_id="dev")
                product_count += 1
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    print(f"  Failed {po.product_id}: {e}")

    print(f"Synced {product_count} products to Redis ({error_count} errors)")

    # Verify
    items, total = await redis.list_products(tenant_id=tenant_id, page_size=5)
    print(f"Redis list_products: {total} total, {len(items)} items on page 1")

    if items:
        item = items[0]
        print(f"  First: {item.product_id} | {item.name} | {item.brand} | {item.category}")


if __name__ == "__main__":
    asyncio.run(main())
