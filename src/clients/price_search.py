"""
全网比价数据源抽象层。

Description:
    为「虚拟买手团」和「直播购物分身」提供统一的比价数据来源，
    支持三种实现，按 auto 顺序依次探测：

    1. ``EsPriceSearchBackend``  —— 读取自建 Elasticsearch 价格索引（全网报价 + 历史曲线）
    2. ``CrawlerPriceSearchBackend`` —— 调用独立部署的采集服务（本项目只定义契约，
       不内置爬虫实现，避免把违反目标站点服务条款的抓取逻辑塞进业务代码）
    3. ``MockPriceSearchBackend`` —— 无外部依赖的确定性模拟数据，产物标记 is_mock=True

    设计原则：数据源可替换、降级显式化。任何模拟数据都会带上 ``is_mock=True``，
    绝不伪装成真实报价。
2026-11-09
"""

import hashlib
import logging
import math
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from src.config.settings import Settings, get_settings
from src.models.buyer import PriceHistoryPoint, PriceQuote

logger = logging.getLogger(__name__)


class PriceSearchError(RuntimeError):
    """比价数据源调用失败。"""


class PriceSearchBackend(ABC):
    """比价数据源基类。

    Attributes:
        name: 数据源标识（es/crawler/mock）。
        is_mock: 是否产生模拟数据。
    """

    name: str = "base"
    is_mock: bool = False

    @abstractmethod
    async def search(
        self, title: str, limit: int = 8, reference_price: float | None = None
    ) -> list[PriceQuote]:
        """检索指定商品在各平台的报价。

        Args:
            title: 商品标题。
            limit: 最多返回条数。
            reference_price: 用户看到的当前价，仅模拟数据源用于让示例更贴近真实场景。

        Returns:
            报价列表，按价格升序。
        """

    @abstractmethod
    async def history(
        self, title: str, days: int = 90, reference_price: float | None = None
    ) -> list[PriceHistoryPoint]:
        """检索指定商品的历史价格曲线。

        Args:
            title: 商品标题。
            days: 回看天数。
            reference_price: 用户看到的当前价，仅模拟数据源使用。

        Returns:
            按日期升序的价格点列表。
        """

    async def close(self) -> None:
        """释放底层连接资源（默认无操作）。"""


class EsPriceSearchBackend(PriceSearchBackend):
    """基于 Elasticsearch 的全网价格索引。

    索引约定（可直接用 ``PUT /product_prices`` 创建）::

        {
          "mappings": {
            "properties": {
              "title":      {"type": "text", "analyzer": "standard"},
              "platform":   {"type": "keyword"},
              "price":      {"type": "double"},
              "currency":   {"type": "keyword"},
              "seller":     {"type": "keyword"},
              "url":        {"type": "keyword"},
              "fetched_at": {"type": "date"}
            }
          }
        }

    Attributes:
        name: 固定为 ``es``。
        is_mock: 固定为 False。
    """

    name = "es"
    is_mock = False

    def __init__(
        self,
        url: str,
        index: str,
        username: str = "",
        password: str = "",
        timeout: float = 8.0,
    ) -> None:
        """初始化 ES 数据源。

        Args:
            url: Elasticsearch 地址。
            index: 索引名。
            username: 用户名（可选）。
            password: 密码（可选）。
            timeout: 请求超时秒数。
        """
        self._url = url.rstrip("/")
        self._index = index
        self._username = username
        self._password = password
        self._timeout = timeout
        self._client: Any = None

    def _get_client(self) -> Any:
        """延迟创建 Elasticsearch 异步客户端。

        Returns:
            AsyncElasticsearch 实例。

        Raises:
            PriceSearchError: 未安装 elasticsearch 依赖。
        """
        if self._client is not None:
            return self._client

        try:
            from elasticsearch import AsyncElasticsearch
        except ImportError as exc:  # pragma: no cover - 依赖未安装时才会走到
            raise PriceSearchError(
                "未安装 elasticsearch 依赖，无法使用 ES 比价数据源。"
                "请执行 uv add elasticsearch，或将 PRICE_SEARCH_BACKEND 设为 crawler/mock。"
            ) from exc

        auth: dict[str, Any] = {}
        if self._username:
            auth = {"basic_auth": (self._username, self._password)}

        self._client = AsyncElasticsearch(hosts=[self._url], request_timeout=self._timeout, **auth)
        return self._client

    async def search(
        self, title: str, limit: int = 8, reference_price: float | None = None
    ) -> list[PriceQuote]:
        """在 ES 中按标题匹配，返回最低价优先的报价列表。

        Args:
            title: 商品标题。
            limit: 最多返回条数。
            reference_price: 未使用，仅为统一接口签名。

        Returns:
            报价列表。

        Raises:
            PriceSearchError: 查询失败。
        """
        client = self._get_client()
        body = {
            "size": limit,
            "query": {"match": {"title": {"query": title, "operator": "or"}}},
            "sort": [{"price": "asc"}],
            "_source": ["platform", "title", "price", "currency", "seller", "url", "fetched_at"],
        }
        try:
            response = await client.search(index=self._index, body=body)
        except Exception as exc:
            raise PriceSearchError(f"ES 比价查询失败: {exc}") from exc

        quotes: list[PriceQuote] = []
        for hit in response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            quotes.append(
                PriceQuote(
                    platform=str(source.get("platform", "unknown")),
                    title=str(source.get("title", title)),
                    price=float(source.get("price", 0)),
                    currency=str(source.get("currency", "CNY")),
                    seller=source.get("seller"),
                    url=source.get("url"),
                    is_mock=False,
                    fetched_at=_parse_datetime(source.get("fetched_at")),
                )
            )
        return quotes

    async def history(
        self, title: str, days: int = 90, reference_price: float | None = None
    ) -> list[PriceHistoryPoint]:
        """按天聚合历史最低价。

        Args:
            title: 商品标题。
            days: 回看天数。
            reference_price: 未使用，仅为统一接口签名。

        Returns:
            按日期升序的价格点列表。

        Raises:
            PriceSearchError: 查询失败。
        """
        client = self._get_client()
        body = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"title": {"query": title, "operator": "or"}}},
                        {"range": {"fetched_at": {"gte": f"now-{days}d/d"}}},
                    ]
                }
            },
            "aggs": {
                "by_day": {
                    "date_histogram": {"field": "fetched_at", "calendar_interval": "day"},
                    "aggs": {"min_price": {"min": {"field": "price"}}},
                }
            },
        }
        try:
            response = await client.search(index=self._index, body=body)
        except Exception as exc:
            raise PriceSearchError(f"ES 历史价格查询失败: {exc}") from exc

        points: list[PriceHistoryPoint] = []
        for bucket in response.get("aggregations", {}).get("by_day", {}).get("buckets", []):
            value = bucket.get("min_price", {}).get("value")
            if value is None:
                continue
            points.append(
                PriceHistoryPoint(date=_parse_date(bucket.get("key_as_string")), price=float(value))
            )
        return points

    async def close(self) -> None:
        """关闭 ES 连接。"""
        if self._client is not None:
            await self._client.close()
            self._client = None


class CrawlerPriceSearchBackend(PriceSearchBackend):
    """独立采集服务数据源。

    本项目只定义调用契约，不内置爬虫实现。约定的接口::

        POST {endpoint}/search
        {"title": "...", "limit": 8}
        -> {"quotes": [{"platform": "...", "title": "...", "price": 199.0, ...}]}

        POST {endpoint}/history
        {"title": "...", "days": 90}
        -> {"history": [{"date": "2026-11-09", "price": 199.0}]}

    采集服务负责遵守目标站点的 robots 协议与服务条款，本服务只消费其结构化结果。

    Attributes:
        name: 固定为 ``crawler``。
        is_mock: 固定为 False。
    """

    name = "crawler"
    is_mock = False

    def __init__(self, endpoint: str, api_key: str = "", timeout: float = 8.0) -> None:
        """初始化采集服务数据源。

        Args:
            endpoint: 采集服务基址。
            api_key: 调用密钥。
            timeout: 请求超时秒数。
        """
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        """构造请求头。

        Returns:
            请求头字典。
        """
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def search(
        self, title: str, limit: int = 8, reference_price: float | None = None
    ) -> list[PriceQuote]:
        """调用采集服务检索报价。

        Args:
            title: 商品标题。
            limit: 最多返回条数。
            reference_price: 未使用，仅为统一接口签名。

        Returns:
            报价列表。

        Raises:
            PriceSearchError: 调用失败或响应格式非法。
        """
        payload = {"title": title, "limit": limit}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._endpoint}/search", json=payload, headers=self._headers()
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise PriceSearchError(f"采集服务比价调用失败: {exc}") from exc

        quotes: list[PriceQuote] = []
        for item in data.get("quotes", []):
            quotes.append(
                PriceQuote(
                    platform=str(item.get("platform", "unknown")),
                    title=str(item.get("title", title)),
                    price=float(item.get("price", 0)),
                    currency=str(item.get("currency", "CNY")),
                    seller=item.get("seller"),
                    url=item.get("url"),
                    is_mock=False,
                    fetched_at=_parse_datetime(item.get("fetched_at")),
                )
            )
        return quotes

    async def history(
        self, title: str, days: int = 90, reference_price: float | None = None
    ) -> list[PriceHistoryPoint]:
        """调用采集服务检索历史价格。

        Args:
            title: 商品标题。
            days: 回看天数。
            reference_price: 未使用，仅为统一接口签名。

        Returns:
            价格点列表。

        Raises:
            PriceSearchError: 调用失败或响应格式非法。
        """
        payload = {"title": title, "days": days}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._endpoint}/history", json=payload, headers=self._headers()
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise PriceSearchError(f"采集服务历史价格调用失败: {exc}") from exc

        points: list[PriceHistoryPoint] = []
        for item in data.get("history", []):
            points.append(
                PriceHistoryPoint(
                    date=_parse_date(item.get("date")),
                    price=float(item.get("price", 0)),
                )
            )
        return points


class MockPriceSearchBackend(PriceSearchBackend):
    """确定性模拟数据源。

    用于本地演示与 CI：不联网、可复现（同一标题永远得到同样的报价），
    但所有产出都标记 ``is_mock=True``，不会伪装成真实价格。

    Attributes:
        name: 固定为 ``mock``。
        is_mock: 固定为 True。
    """

    name = "mock"
    is_mock = True

    # 模拟平台池
    _PLATFORMS = ("京东", "天猫", "拼多多", "抖音商城", "唯品会")
    # 未提供参考价时的基准价生成参数
    _FALLBACK_BASE_MIN = 79.0
    _FALLBACK_BASE_RANGE = 900

    def __init__(self, base_seed: str = "") -> None:
        """初始化模拟数据源。

        Args:
            base_seed: 额外随机种子前缀。
        """
        self._seed = base_seed

    def _digest(self, title: str) -> int:
        """由标题生成稳定的整数种子。

        Args:
            title: 商品标题。

        Returns:
            非负整数种子。
        """
        raw = f"{self._seed}:{title}".encode()
        return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")

    def _base_price(self, title: str, reference_price: float | None) -> float:
        """确定模拟价格的基准值。

        有参考价时以参考价为中心上下浮动，这样演示数据与商品真实价位一致，
        不会出现「当前 ¥199、历史最低 ¥848」这种自相矛盾的结论。

        Args:
            title: 商品标题。
            reference_price: 参考价（通常是商品当前价）。

        Returns:
            基准价。
        """
        if reference_price and reference_price > 0:
            return float(reference_price)
        seed = self._digest(title)
        return self._FALLBACK_BASE_MIN + (seed % self._FALLBACK_BASE_RANGE)

    async def search(
        self, title: str, limit: int = 8, reference_price: float | None = None
    ) -> list[PriceQuote]:
        """生成各平台的模拟报价。

        Args:
            title: 商品标题。
            limit: 最多返回条数。
            reference_price: 参考价，用于让模拟报价贴近真实价位。

        Returns:
            按价格升序的模拟报价列表。
        """
        seed = self._digest(title)
        base = self._base_price(title, reference_price)
        count = max(1, min(limit, len(self._PLATFORMS)))
        quotes: list[PriceQuote] = []
        for index, platform in enumerate(self._PLATFORMS[:count]):
            # 各平台在基准价的 0.88-1.15 倍之间波动
            spread = 0.88 + ((seed >> (index * 7)) % 28) / 100.0
            price = round(base * spread * (1 - index * 0.01), 2)
            quotes.append(
                PriceQuote(
                    platform=platform,
                    title=title,
                    price=max(1.0, price),
                    currency="CNY",
                    seller=f"{platform}官方旗舰店" if index % 2 == 0 else f"{platform}自营",
                    url=f"https://example.invalid/{platform}/{seed % 10_000}",
                    is_mock=True,
                    fetched_at=datetime.now(),
                )
            )
        return sorted(quotes, key=lambda quote: quote.price)

    async def history(
        self, title: str, days: int = 90, reference_price: float | None = None
    ) -> list[PriceHistoryPoint]:
        """生成模拟历史价格曲线（带周期性促销波动）。

        Args:
            title: 商品标题。
            days: 回看天数。
            reference_price: 参考价，用于让曲线落在合理价位。

        Returns:
            按日期升序的模拟价格点列表。
        """
        seed = self._digest(title)
        base = self._base_price(title, reference_price)
        today = date.today()
        points: list[PriceHistoryPoint] = []
        for offset in range(days, -1, -1):
            day = today - timedelta(days=offset)
            # 以 30 天为周期的促销节律 + 轻微抖动
            wave = math.sin((days - offset) / 30.0 * 2 * math.pi) * 0.08
            noise = (((seed >> (offset % 17)) % 41) - 20) / 1000.0  # ±2%
            price = round(base * (1 + wave + noise), 2)
            points.append(PriceHistoryPoint(date=day, price=max(1.0, price)))
        return points


def _parse_datetime(value: Any) -> datetime | None:
    """把 ES/HTTP 返回的时间字段解析为 datetime。

    Args:
        value: 原始值，可能是 ISO 字符串、毫秒时间戳或 None。

    Returns:
        解析结果，无法解析时返回 None。
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_date(value: Any) -> date:
    """把 ES 返回的日期字段解析为 date。

    Args:
        value: 原始值，可能是 ``2026-11-09`` 或 ``2026-11-09T00:00:00.000Z``。

    Returns:
        解析结果；无法解析时返回今天。
    """
    parsed = _parse_datetime(value)
    return parsed.date() if parsed else date.today()


_backend: PriceSearchBackend | None = None


def build_price_search_backend(settings: Settings | None = None) -> PriceSearchBackend:
    """按配置构造比价数据源（不做连通性探测）。

    Args:
        settings: 配置实例，默认取全局单例。

    Returns:
        数据源实例。

    Raises:
        PriceSearchError: 配置为 mock 但禁用了模拟数据源。
    """
    settings = settings or get_settings()
    choice = (settings.price_search_backend or "auto").strip().lower()

    if choice == "es":
        if not settings.elasticsearch_url:
            raise PriceSearchError("PRICE_SEARCH_BACKEND=es 但未配置 ELASTICSEARCH_URL")
        return EsPriceSearchBackend(
            url=settings.elasticsearch_url,
            index=settings.elasticsearch_index,
            username=settings.elasticsearch_username,
            password=settings.elasticsearch_password,
            timeout=settings.price_search_timeout_seconds,
        )

    if choice == "crawler":
        if not settings.price_crawler_endpoint:
            raise PriceSearchError(
                "PRICE_SEARCH_BACKEND=crawler 但未配置 PRICE_CRAWLER_ENDPOINT"
            )
        return CrawlerPriceSearchBackend(
            endpoint=settings.price_crawler_endpoint,
            api_key=settings.price_crawler_api_key,
            timeout=settings.price_search_timeout_seconds,
        )

    if choice == "mock" or choice == "auto":
        if not settings.allow_mock_sources:
            raise PriceSearchError(
                "未配置 ES 或采集服务，且 ALLOW_MOCK_SOURCES=False，"
                "无法提供比价数据。请配置 ELASTICSEARCH_URL 或 PRICE_CRAWLER_ENDPOINT。"
            )
        return MockPriceSearchBackend()

    raise PriceSearchError(f"未知的比价数据源: {choice}（可选 auto/es/crawler/mock）")


def get_price_search_backend(settings: Settings | None = None) -> PriceSearchBackend:
    """获取比价数据源单例。

    进程内缓存，避免每次请求都重建客户端。

    Args:
        settings: 配置实例，默认取全局单例。

    Returns:
        数据源实例。
    """
    global _backend
    if _backend is None:
        _backend = build_price_search_backend(settings)
    return _backend


def reset_price_search_backend() -> None:
    """清空数据源单例（测试与运行时切换配置时使用）。"""
    global _backend
    _backend = None
