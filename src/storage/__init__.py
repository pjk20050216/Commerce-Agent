"""
文件存储模块。

Description:
    提供统一的存储后端抽象、本地实现与工厂函数，
    用于图片、视频及上传文件的持久化。2026-09-03
"""

from src.storage.base import StorageBackend
from src.storage.factory import get_storage_backend, reset_storage_backend
from src.storage.local import LocalStorageBackend

__all__ = [
    "LocalStorageBackend",
    "StorageBackend",
    "get_storage_backend",
    "reset_storage_backend",
]
