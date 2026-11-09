"""刊登推送 API 测试（mock 数据库层）。"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app

from src.db.listing_models import TaskResultPO


@pytest.fixture(autouse=True)
def _disable_auth() -> None:
    """禁用 auth 以便测试。"""
    from src.config.settings import get_settings

    settings = get_settings()
    settings.auth_enabled = False


def _make_task_po(**kwargs) -> MagicMock:
    """构造模拟 ListingTaskPO。"""
    from src.db.listing_models import ListingTaskPO as _TaskPO

    defaults = {
        "id": 1,
        "tenant_id": "test-tenant",
        "product_sku": "PUSH-001",
        "target_platforms": ["amazon"],
        "status": "pending",
        "workflow_state": None,
        "auto_execute": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    po = MagicMock(spec=_TaskPO)
    for k, v in defaults.items():
        setattr(po, k, v)
    return po


def _make_result_po(**kwargs) -> MagicMock:
    """构造模拟 TaskResultPO。"""
    defaults = {
        "id": 1,
        "task_id": 1,
        "platform": "amazon",
        "success": True,
        "result_data": {
            "listing_id": "B08XYZ",
            "url": "https://amazon.com/dp/B08XYZ",
            "error": None,
        },
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    po = MagicMock(spec=TaskResultPO)
    for k, v in defaults.items():
        setattr(po, k, v)
    return po


def _mock_get_db():
    """创建 get_db mock 上下文管理器。"""
    mock_session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm, mock_session


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestListingPushAPI:
    """测试刊登推送 API。"""

    def test_push_task_not_found(self, client: TestClient) -> None:
        """测试推送不存在的任务。"""
        with patch(
            "src.api.router.listing_push._load_domain_objects", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = None

            response = client.post("/api/v1/listing/tasks/9999/push")
            data = response.json()
            assert data["code"] == 404

    def test_get_push_results(self, client: TestClient) -> None:
        """测试查询推送结果。"""
        mock_result_po = _make_result_po(task_id=1, platform="amazon", success=True)
        mock_repo = AsyncMock()
        mock_repo.list = AsyncMock(return_value=[mock_result_po])

        cm, _ = _mock_get_db()

        with (
            patch("src.api.router.listing_push.get_db", return_value=cm),
            patch("src.api.router.listing_push.BaseRepository", return_value=mock_repo),
        ):
            result_resp = client.get("/api/v1/listing/tasks/1/push-results")
            assert result_resp.status_code == 200
            data = result_resp.json()
            assert data["code"] == 200
            assert len(data["data"]) == 1

    def test_get_push_results_not_found(self, client: TestClient) -> None:
        """测试查询不存在的推送结果。"""
        mock_repo = AsyncMock()
        mock_repo.list = AsyncMock(return_value=[])

        cm, _ = _mock_get_db()

        with (
            patch("src.api.router.listing_push.get_db", return_value=cm),
            patch("src.api.router.listing_push.BaseRepository", return_value=mock_repo),
        ):
            response = client.get("/api/v1/listing/tasks/9999/push-results")
            data = response.json()
            assert data["code"] == 404
