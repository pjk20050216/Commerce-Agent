"""
文件存储抽象层。

Description:
    定义统一的存储后端接口，屏蔽本地文件系统与云存储（OSS）的差异，
    供图片、视频以及商品上传文件使用。2026-09-03
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """存储后端抽象基类。

    Attributes:
        base_path: 本地存储根路径（云存储实现可为空）。

    Example:
        >>> class MemoryBackend(StorageBackend):
        ...     async def save(self, data, key, content_type=None):
        ...         return f"/static/{key}"
    """

    def __init__(self, base_path: str | None = None) -> None:
        """初始化存储后端。

        Args:
            base_path: 本地存储根路径。
        """
        self.base_path = base_path

    @abstractmethod
    async def save(self, data: bytes, key: str, content_type: str | None = None) -> str:
        """保存数据并返回可访问地址。

        Args:
            data: 文件二进制内容。
            key: 存储键名（相对路径）。
            content_type: 内容类型，如 image/png。

        Returns:
            文件访问地址。
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除文件。

        Args:
            key: 存储键名。

        Returns:
            删除成功（或文件本不存在）时返回 True。
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """判断文件是否存在。

        Args:
            key: 存储键名。

        Returns:
            文件存在时返回 True。
        """
        raise NotImplementedError

    @abstractmethod
    def get_url(self, key: str) -> str:
        """获取文件的访问地址。

        Args:
            key: 存储键名。

        Returns:
            可访问的 URL 路径。
        """
        raise NotImplementedError
