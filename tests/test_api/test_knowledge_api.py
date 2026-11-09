"""
知识库 API 测试。

Description:
    测试知识库管理相关 API 端点。
@version 1.0.0
2026-09-08
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端。"""
    return TestClient(app)


@pytest.fixture
def mock_session() -> MagicMock:
    """创建模拟数据库会话。"""
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


class TestKnowledgeDocumentAPI:
    """知识库文档 API 测试。"""

    def test_list_documents(self, client: TestClient) -> None:
        """测试获取文档列表。"""
        response = client.get("/api/v1/knowledge/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_get_stats(self, client: TestClient) -> None:
        """测试获取统计信息。"""
        response = client.get("/api/v1/knowledge/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
