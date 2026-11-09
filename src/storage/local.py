"""
本地文件系统存储后端。

Description:
    将文件写入本地磁盘目录，并通过 /static 静态路由对外暴露。2026-09-03
"""

import asyncio
import hashlib
import uuid
from pathlib import Path

from src.storage.base import StorageBackend

STATIC_PREFIX = "/static"


class LocalStorageBackend(StorageBackend):
    """本地存储后端。

    Attributes:
        base_path: 本地存储根目录。

    Example:
        >>> backend = LocalStorageBackend(base_path="./output")
        >>> backend.get_url("images/a.png")
        '/static/images/a.png'
    """

    def __init__(self, base_path: str = "./output") -> None:
        """初始化本地存储后端。

        Args:
            base_path: 存储根目录，不存在时会自动创建。
        """
        super().__init__(base_path=base_path)
        self._base_path = base_path
        self._root = Path(base_path)
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """将存储键解析为绝对路径，并阻止目录穿越。

        Args:
            key: 存储键名。

        Returns:
            文件绝对路径。

        Raises:
            ValueError: 键名试图跳出存储根目录时抛出。
        """
        root = self._root.resolve()
        target = (root / key.lstrip("/")).resolve()
        if not str(target).startswith(str(root)):
            raise ValueError(f"非法的存储键名: {key}")
        return target

    async def save(self, data: bytes, key: str, content_type: str | None = None) -> str:
        """保存数据到本地磁盘。

        Args:
            data: 文件二进制内容。
            key: 存储键名（相对路径）。
            content_type: 内容类型，本地存储忽略该参数。

        Returns:
            形如 /static/<key> 的访问地址。

        Example:
            >>> # url = await backend.save(b"hi", "images/a.png")
        """
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return self.get_url(key)

    async def delete(self, key: str) -> bool:
        """删除文件。

        Args:
            key: 存储键名。

        Returns:
            始终返回 True，文件不存在时不报错。
        """
        self._resolve(key).unlink(missing_ok=True)
        return True

    async def exists(self, key: str) -> bool:
        """判断文件是否存在。

        Args:
            key: 存储键名。

        Returns:
            文件存在时返回 True。
        """
        return self._resolve(key).is_file()

    def get_url(self, key: str) -> str:
        """获取文件访问地址。

        Args:
            key: 存储键名。

        Returns:
            形如 /static/<key> 的地址。
        """
        return f"{STATIC_PREFIX}/{key.lstrip('/')}"

    @staticmethod
    def generate_key(prefix: str, extension: str | None = None) -> str:
        """生成唯一存储键名。

        Args:
            prefix: 前缀目录，如 images。
            extension: 文件扩展名（不含点号）。

        Returns:
            形如 images/<32位hex>.png 的键名。

        Example:
            >>> LocalStorageBackend.generate_key("images", "png").startswith("images/")
            True
        """
        name = uuid.uuid4().hex
        if extension:
            name = f"{name}.{extension.lstrip('.')}"
        return f"{prefix}/{name}"

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """计算数据的 SHA-256 摘要。

        Args:
            data: 二进制内容。

        Returns:
            十六进制摘要字符串。

        Example:
            >>> len(LocalStorageBackend.compute_sha256(b"hello world"))
            64
        """
        return hashlib.sha256(data).hexdigest()
