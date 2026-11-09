"""
存储后端工厂。

Description:
    根据配置创建对应的存储后端实例，并对实例做进程内缓存复用。
    当前支持本地存储；OSS 未配置时自动回退到本地存储。2026-09-03
"""

import logging
from functools import lru_cache

from src.config.settings import get_settings
from src.storage.base import StorageBackend
from src.storage.local import LocalStorageBackend

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_storage_backend() -> StorageBackend:
    """获取当前配置对应的存储后端。

    Returns:
        存储后端实例，多次调用返回同一实例。

    Example:
        >>> backend = get_storage_backend()  # doctest: +SKIP
    """
    settings = get_settings()
    config = settings.get_storage_config()

    if config.get("type") == "oss":
        endpoint = config.get("endpoint")
        bucket = config.get("bucket")
        access_key = config.get("access_key")
        secret_key = config.get("secret_key")
        if endpoint and bucket and access_key and secret_key:
            try:
                from src.storage.oss import OSSStorageBackend

                return OSSStorageBackend(
                    endpoint=endpoint,
                    bucket=bucket,
                    access_key=access_key,
                    secret_key=secret_key,
                )
            except (ImportError, RuntimeError) as exc:  # pragma: no cover - 依赖可选
                logger.warning("OSS 存储不可用，回退到本地存储: %s", exc)
        else:
            logger.warning("OSS 配置不完整，回退到本地存储")

    return LocalStorageBackend(base_path=str(config.get("path") or "./output"))


def reset_storage_backend() -> None:
    """清空存储后端缓存。

    便于测试或运行时切换存储配置后重新构造实例。

    Example:
        >>> reset_storage_backend()
    """
    get_storage_backend.cache_clear()
