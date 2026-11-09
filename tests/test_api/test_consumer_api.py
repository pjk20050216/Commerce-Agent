"""消费者侧 API 测试（依赖 PostgreSQL）。

这些用例直接打真实数据库，用于验证「工作流 → 落库 → 查询」链路。
数据库不可达时整体跳过，避免在无 Docker 环境下误报失败。
"""

import socket
import uuid

import pytest
from fastapi.testclient import TestClient
from main import app

from src.config.settings import get_settings


def _db_reachable() -> bool:
    """探测 PostgreSQL 端口是否可连接。

    Returns:
        可连接返回 True。
    """
    settings = get_settings()
    try:
        with socket.create_connection(
            (settings.postgres_host, settings.postgres_port), timeout=2
        ):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _db_reachable(), reason="需要可用的 PostgreSQL（docker compose up -d postgres）"
)


@pytest.fixture(autouse=True)
def _disable_auth() -> None:
    """禁用鉴权，使用 dev 租户。"""
    settings = get_settings()
    settings.auth_enabled = False
    settings.consumer_features_enabled = True


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端。

    必须用 ``with`` 进入上下文：这样整组请求共享同一个事件循环，
    否则每次请求都会新建 loop，复用 asyncpg 连接时会报
    ``'NoneType' object has no attribute 'send'``。
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_id() -> str:
    """每次运行唯一的用户 ID，避免历史数据干扰断言。"""
    return f"u_{uuid.uuid4().hex[:10]}"


class TestBuyerAPI:
    """虚拟买手团接口。"""

    def test_create_decision_and_query(self, client: TestClient, user_id: str) -> None:
        """创建决策卡后应能按 card_id 与用户查询到。"""
        response = client.post(
            "/api/v1/buyer/decisions",
            json={
                "user_id": user_id,
                "candidate": {
                    "title": "极简风纯色棉质衬衫",
                    "price": 199,
                    "category": "女装",
                    "tags": ["极简", "纯色"],
                    "reviews": ["掉色严重", "尺码偏小"],
                    "return_rate": 0.23,
                },
                "history": [
                    {
                        "item_id": "1",
                        "title": "简约纯色T恤",
                        "tags": ["极简"],
                        "price": 89,
                        "action": "purchase",
                    }
                ],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == 200
        card = payload["data"]
        assert card["user_id"] == user_id
        assert 0 <= card["score"]["overall"] <= 100
        assert card["candidate"]["title"] == "极简风纯色棉质衬衫"

        detail = client.get(f"/api/v1/buyer/decisions/{card['card_id']}")
        assert detail.status_code == 200
        assert detail.json()["data"]["card_id"] == card["card_id"]

        listing = client.get("/api/v1/buyer/decisions", params={"user_id": user_id})
        assert listing.status_code == 200
        items = listing.json()["data"]
        assert len(items) == 1
        assert items[0]["card_id"] == card["card_id"]

    def test_decision_requires_user_id(self, client: TestClient) -> None:
        """缺少 user_id 应返回 422。"""
        response = client.post(
            "/api/v1/buyer/decisions",
            json={"candidate": {"title": "商品", "price": 10}},
        )
        assert response.status_code == 422

    def test_compare_endpoint(self, client: TestClient) -> None:
        """独立比价接口返回比价结论与曲线。"""
        response = client.post(
            "/api/v1/buyer/compare",
            json={"title": "极简风纯棉衬衫", "current_price": 199},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["verdict"]
        assert data["quotes"]
        assert data["advice"]
        assert data["is_mock"] is True

    def test_unknown_card_returns_404(self, client: TestClient) -> None:
        """不存在的决策卡返回 404。"""
        response = client.get("/api/v1/buyer/decisions/card_not_exist")
        assert response.status_code == 404


class TestDisputeAPI:
    """纠纷仲裁接口。"""

    def test_case_lifecycle(self, client: TestClient) -> None:
        """受理 → 查询 → 重新生成话术。"""
        response = client.post(
            "/api/v1/dispute/cases",
            json={
                "order": {
                    "order_id": f"ORD-{uuid.uuid4().hex[:8]}",
                    "platform": "淘宝",
                    "amount": 199,
                    "product_title": "纯棉衬衫",
                },
                "claim_text": "衣服掉色严重，要求退货退款",
                "chat_log": [
                    {"speaker": "consumer", "content": "掉色严重，要求退货"},
                    {"speaker": "merchant", "content": "拆封了，拒绝退款"},
                ],
                "logistics": [{"status": "已签收", "description": "本人签收"}],
                "unboxing": [
                    {
                        "image_url": "https://example.invalid/a.jpg",
                        "description": "领口掉色",
                    }
                ],
            },
        )
        assert response.status_code == 200
        result = response.json()["data"]
        case_id = result["case_id"]
        assert result["verdict"]["responsibility"] == "merchant"
        assert len(result["drafts"]) == 3
        assert result["disclaimer"]

        detail = client.get(f"/api/v1/dispute/cases/{case_id}")
        assert detail.status_code == 200
        assert detail.json()["data"]["case_id"] == case_id

        draft = client.post(
            f"/api/v1/dispute/cases/{case_id}/draft",
            json={"tone": "negotiation"},
        )
        assert draft.status_code == 200
        assert draft.json()["data"]["tone"] == "negotiation"

    def test_unknown_case_returns_404(self, client: TestClient) -> None:
        """不存在的案件返回 404。"""
        assert client.get("/api/v1/dispute/cases/case_not_exist").status_code == 404
        assert (
            client.post(
                "/api/v1/dispute/cases/case_not_exist/draft", json={"tone": "appeal"}
            ).status_code
            == 404
        )


class TestLiveAPI:
    """直播购物分身接口。"""

    def test_session_lifecycle(self, client: TestClient) -> None:
        """创建 → 推入事件 → 查快照 → 列表 → 结束。"""
        created = client.post(
            "/api/v1/live/sessions",
            json={"room_id": f"room-{uuid.uuid4().hex[:6]}", "title": "秋冬衬衫专场"},
        )
        assert created.status_code == 201
        session_id = created.json()["data"]["session_id"]

        ingest = client.post(
            f"/api/v1/live/sessions/{session_id}/ingest",
            json={
                "segments": [
                    {"start_seconds": 0, "end_seconds": 8, "text": "限量500件，拍一发三"},
                    {"start_seconds": 8, "end_seconds": 15, "text": "到手价199，只有今晚"},
                ],
                "danmaku": [{"text": "冲了"}, {"text": "太贵了"}],
                "current_product": "纯棉衬衫",
            },
        )
        assert ingest.status_code == 200
        snapshot = ingest.json()["data"]
        assert snapshot["key_points"]
        assert snapshot["price_alert"] is not None
        assert snapshot["processed_segments"] == 2
        assert snapshot["processed_danmaku"] == 2

        fetched = client.get(f"/api/v1/live/sessions/{session_id}/snapshot")
        assert fetched.status_code == 200
        assert fetched.json()["data"]["session_id"] == session_id

        listing = client.get("/api/v1/live/sessions", params={"limit": 50})
        assert listing.status_code == 200
        assert any(item["session_id"] == session_id for item in listing.json()["data"])

        ended = client.post(f"/api/v1/live/sessions/{session_id}/end")
        assert ended.status_code == 200
        assert ended.json()["data"]["status"] == "ended"

    def test_price_check(self, client: TestClient) -> None:
        """一键比价返回提醒与建议。"""
        response = client.post(
            "/api/v1/live/price-check", json={"title": "纯棉衬衫", "price": 99}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["trigger"]["price"] == 99.0
        assert data["advice"]
        assert data["is_mock"] is True

    def test_missing_session_returns_404(self, client: TestClient) -> None:
        """不存在的直播会话返回 404。"""
        assert (
            client.get("/api/v1/live/sessions/live_not_exist/snapshot").status_code == 404
        )


class TestFeatureGate:
    """消费者侧功能开关。"""

    def test_disabled_returns_403(
        self, client: TestClient, user_id: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """开关关闭时接口返回 403。"""
        monkeypatch.setattr(get_settings(), "consumer_features_enabled", False)

        response = client.post(
            "/api/v1/buyer/decisions",
            json={"user_id": user_id, "candidate": {"title": "商品", "price": 10}},
        )
        assert response.status_code == 403
        assert "未启用" in response.json()["detail"]
