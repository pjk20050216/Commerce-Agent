"""
测试配置。
"""

import pytest


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """模拟环境变量。"""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test_api_key")
    monkeypatch.setenv("KLING_API_KEY", "test_kling_key")


@pytest.fixture(autouse=True)
def _reset_db_manager() -> None:
    """每个用例结束后重置全局数据库管理器。

    FastAPI 的 TestClient 会为每个用例创建独立的事件循环，而
    ``src.db.postgres._db_manager`` 是模块级单例，其 asyncpg 连接绑定在
    创建时的事件循环上。若不重置，后续用例复用旧连接会触发
    ``RuntimeError: Event loop is closed`` 或 ``NoneType has no attribute 'send'``。
    """
    yield
    try:
        from src.db import postgres

        postgres._db_manager = None
    except Exception:  # pragma: no cover - 清理失败不应影响用例结果
        pass
