"""适配器配置管理器测试。"""

import pytest

from src.agents.adapter_config import AdapterConfigManager
from src.models.listing import Platform


class TestAdapterConfigManager:
    """测试适配器配置管理器。"""

    @pytest.fixture
    def manager(self) -> AdapterConfigManager:
        """创建配置管理器实例。"""
        mgr = AdapterConfigManager()
        mgr._cache.clear()
        return mgr

    def test_singleton(self) -> None:
        """测试管理器是单例。"""
        m1 = AdapterConfigManager()
        m2 = AdapterConfigManager()
        assert m1 is m2

    @pytest.mark.asyncio
    async def test_cache_hit(self, manager: AdapterConfigManager) -> None:
        """测试缓存命中（tenant-aware key）。"""
        key = ("tenant-x", Platform.AMAZON, "shop-1")
        cached = {"client_id": "cached"}
        manager._cache[key] = (cached, 9999999999.0)  # 很久才过期

        result = await manager.get_config(Platform.AMAZON, "shop-1", tenant_id="tenant-x")
        assert result == cached
        assert result is not cached  # 返回副本，不是同一对象

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, manager: AdapterConfigManager) -> None:
        """测试清除缓存（tenant-aware）。"""
        key = ("tenant-e", Platform.SHOPIFY, "shop-3")
        manager._cache[key] = ({"test": True}, 9999999999.0)
        await manager.invalidate_cache(Platform.SHOPIFY, "shop-3", tenant_id="tenant-e")
        assert key not in manager._cache

    @pytest.mark.asyncio
    async def test_invalidate_all_platform_single_tenant(
        self, manager: AdapterConfigManager
    ) -> None:
        """测试清除某租户某平台所有店铺的缓存。"""
        manager._cache[("tenant-f", Platform.AMAZON, "shop-1")] = ({"a": 1}, 9999999999.0)
        manager._cache[("tenant-f", Platform.AMAZON, "shop-2")] = ({"b": 2}, 9999999999.0)
        manager._cache[("tenant-f", Platform.EBAY, "shop-1")] = ({"c": 3}, 9999999999.0)
        manager._cache[("tenant-g", Platform.AMAZON, "shop-1")] = ({"d": 4}, 9999999999.0)

        await manager.invalidate_cache(Platform.AMAZON, tenant_id="tenant-f")

        assert ("tenant-f", Platform.AMAZON, "shop-1") not in manager._cache
        assert ("tenant-f", Platform.AMAZON, "shop-2") not in manager._cache
        assert ("tenant-f", Platform.EBAY, "shop-1") in manager._cache
        assert ("tenant-g", Platform.AMAZON, "shop-1") in manager._cache

    @pytest.mark.asyncio
    async def test_invalidate_all_tenants(self, manager: AdapterConfigManager) -> None:
        """测试不指定 tenant 时清除所有租户的该平台缓存。"""
        manager._cache[("tenant-h", Platform.AMAZON, "shop-1")] = ({"a": 1}, 9999999999.0)
        manager._cache[("tenant-i", Platform.AMAZON, "shop-2")] = ({"b": 2}, 9999999999.0)
        manager._cache[("tenant-h", Platform.EBAY, "shop-1")] = ({"c": 3}, 9999999999.0)

        await manager.invalidate_cache(Platform.AMAZON)

        assert ("tenant-h", Platform.AMAZON, "shop-1") not in manager._cache
        assert ("tenant-i", Platform.AMAZON, "shop-2") not in manager._cache
        assert ("tenant-h", Platform.EBAY, "shop-1") in manager._cache

