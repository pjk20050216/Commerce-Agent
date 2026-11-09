"""
直播购物分身 API 路由。

Description:
    提供直播会话创建、批量事件推入、快照查询、结束会话、一键比价
    以及 WebSocket 实时推送接口。

    一次 ingest 只处理增量批次，返回合并后的完整快照，
    前端据此刷新「关键信息 + 弹幕口碑 + 比价提醒」三块面板。2026-11-09
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, WebSocket, status
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from src.agents.live_price_comparator import PriceComparatorAgent
from src.api.deps import AuthDep
from src.api.schema.common import ApiResponse
from src.api.schema.live import (
    CreateLiveSessionRequest,
    LivePriceCheckRequest,
    LiveSessionSummary,
)
from src.auth import authenticate_websocket
from src.config.settings import get_settings
from src.db.consumer_models import LiveSessionPO, utcnow
from src.db.postgres import get_db_session
from src.db.repository import TenantRepository
from src.graph.live_workflow import LiveWorkflow
from src.models.live import (
    DanmakuItem,
    KeyPointKind,
    LiveIngestRequest,
    LiveKeyPoint,
    LivePriceAlert,
    LiveSnapshot,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _ensure_enabled() -> None:
    """校验消费者侧能力开关。

    Raises:
        HTTPException: 功能未启用时返回 403。
    """
    if not get_settings().consumer_features_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="消费者侧能力未启用，请设置 CONSUMER_FEATURES_ENABLED=true",
        )


def _to_summary(po: LiveSessionPO) -> LiveSessionSummary:
    """把 ORM 记录转换为列表项。

    Args:
        po: 直播会话记录。

    Returns:
        列表项。
    """
    return LiveSessionSummary(
        session_id=po.session_id,
        room_id=po.room_id,
        title=po.title,
        status=po.status,
        updated_at=po.updated_at,
    )


async def _load_payload(session_id: str, tenant_id: str) -> dict:
    """读取会话快照原始 JSON。

    Args:
        session_id: 会话标识。
        tenant_id: 租户 ID。

    Returns:
        快照 JSON。

    Raises:
        HTTPException: 会话不存在时返回 404。
    """
    async with get_db_session() as session:
        stmt = select(LiveSessionPO).where(
            LiveSessionPO.tenant_id == tenant_id,
            LiveSessionPO.session_id == session_id,
        )
        record = (await session.execute(stmt)).scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="直播会话不存在")
    return record.payload or {}


async def _save_snapshot(session_id: str, tenant_id: str, snapshot: LiveSnapshot) -> None:
    """写回最新快照。

    Args:
        session_id: 会话标识。
        tenant_id: 租户 ID。
        snapshot: 最新快照。

    Raises:
        HTTPException: 会话不存在时返回 404。
    """
    async with get_db_session() as session:
        stmt = select(LiveSessionPO).where(
            LiveSessionPO.tenant_id == tenant_id,
            LiveSessionPO.session_id == session_id,
        )
        record = (await session.execute(stmt)).scalar_one_or_none()
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="直播会话不存在"
            )
        record.payload = snapshot.model_dump(mode="json")
        record.status = snapshot.status
        record.updated_at = utcnow()


@router.post(
    "/sessions",
    response_model=ApiResponse[LiveSnapshot],
    status_code=status.HTTP_201_CREATED,
    summary="创建直播会话",
)
async def create_session(
    request: CreateLiveSessionRequest,
    auth: AuthDep,
) -> ApiResponse[LiveSnapshot]:
    """创建直播会话并返回初始快照。

    Args:
        request: 创建请求。
        auth: 认证上下文。

    Returns:
        初始快照。
    """
    _ensure_enabled()

    workflow = LiveWorkflow(settings=get_settings())
    session_id = f"live_{datetime.now():%Y%m%d%H%M%S}_{auth.tenant_id}"
    snapshot = await workflow.process(
        session_id=session_id,
        room_id=request.room_id,
        title=request.title,
        tenant_id=auth.tenant_id,
    )

    try:
        async with get_db_session() as session:
            repo = TenantRepository(LiveSessionPO, session)
            await repo.create_for_tenant(
                auth.tenant_id,
                session_id=session_id,
                room_id=request.room_id,
                title=request.title,
                status="running",
                payload=snapshot.model_dump(mode="json"),
            )
    except Exception as exc:
        logger.warning("直播会话落库失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"直播会话创建失败: {exc}",
        ) from exc

    return ApiResponse(code=200, message="会话已创建", data=snapshot)


@router.get(
    "/sessions",
    response_model=ApiResponse[list[LiveSessionSummary]],
    summary="直播会话列表",
)
async def list_sessions(
    auth: AuthDep,
    session_status: str | None = Query(default=None, alias="status", description="按状态过滤"),
    limit: int = Query(default=20, ge=1, le=100, description="返回条数"),
) -> ApiResponse[list[LiveSessionSummary]]:
    """查询当前租户的直播会话。

    Args:
        auth: 认证上下文。
        session_status: 可选的状态过滤。
        limit: 返回条数。

    Returns:
        会话列表项。
    """
    _ensure_enabled()

    async with get_db_session() as session:
        repo = TenantRepository(LiveSessionPO, session)
        filters = {"status": session_status} if session_status else {}
        records = await repo.list_for_tenant(auth.tenant_id, **filters)

    ordered = sorted(
        records,
        key=lambda item: item.updated_at or datetime.min,
        reverse=True,
    )[:limit]
    return ApiResponse(
        code=200,
        message="success",
        data=[_to_summary(item) for item in ordered],
    )


@router.get(
    "/sessions/{session_id}/snapshot",
    response_model=ApiResponse[LiveSnapshot],
    summary="获取直播快照",
)
async def get_snapshot(session_id: str, auth: AuthDep) -> ApiResponse[LiveSnapshot]:
    """获取指定会话的最新快照。

    Args:
        session_id: 会话标识。
        auth: 认证上下文。

    Returns:
        最新快照。
    """
    _ensure_enabled()

    payload = await _load_payload(session_id, auth.tenant_id)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话暂无快照数据"
        )
    return ApiResponse(
        code=200, message="success", data=LiveSnapshot.model_validate(payload)
    )


@router.post(
    "/sessions/{session_id}/ingest",
    response_model=ApiResponse[LiveSnapshot],
    summary="推入直播事件",
)
async def ingest(
    session_id: str,
    request: LiveIngestRequest,
    auth: AuthDep,
) -> ApiResponse[LiveSnapshot]:
    """推入一批字幕/弹幕并返回合并后的快照。

    Args:
        session_id: 会话标识。
        request: 事件批次。
        auth: 认证上下文。

    Returns:
        合并后的快照。
    """
    _ensure_enabled()

    payload = await _load_payload(session_id, auth.tenant_id)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话暂无快照数据"
        )

    workflow = LiveWorkflow(settings=get_settings())
    snapshot = await workflow.process(
        session_id=session_id,
        segments=request.segments,
        danmaku=request.danmaku,
        current_product=request.current_product,
        snapshot=LiveSnapshot.model_validate(payload),
        tenant_id=auth.tenant_id,
    )
    await _save_snapshot(session_id, auth.tenant_id, snapshot)
    return ApiResponse(code=200, message="success", data=snapshot)


@router.post(
    "/sessions/{session_id}/end",
    response_model=ApiResponse[LiveSnapshot],
    summary="结束直播会话",
)
async def end_session(session_id: str, auth: AuthDep) -> ApiResponse[LiveSnapshot]:
    """结束会话并返回最终快照。

    Args:
        session_id: 会话标识。
        auth: 认证上下文。

    Returns:
        最终快照。
    """
    _ensure_enabled()

    payload = await _load_payload(session_id, auth.tenant_id)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话暂无快照数据"
        )

    snapshot = LiveSnapshot.model_validate(payload)
    snapshot.status = "ended"
    snapshot.updated_at = datetime.now()
    await _save_snapshot(session_id, auth.tenant_id, snapshot)

    async with get_db_session() as session:
        stmt = select(LiveSessionPO).where(
            LiveSessionPO.tenant_id == auth.tenant_id,
            LiveSessionPO.session_id == session_id,
        )
        record = (await session.execute(stmt)).scalar_one_or_none()
        if record is not None:
            record.ended_at = utcnow()

    return ApiResponse(code=200, message="会话已结束", data=snapshot)


@router.post(
    "/price-check",
    response_model=ApiResponse[LivePriceAlert],
    summary="一键比价",
)
async def price_check(
    request: LivePriceCheckRequest,
    auth: AuthDep,
) -> ApiResponse[LivePriceAlert]:
    """对一次报价执行全网比价。

    Args:
        request: 比价请求。
        auth: 认证上下文。

    Returns:
        比价提醒。

    Raises:
        HTTPException: 无法完成比价时返回 502。
    """
    _ensure_enabled()

    agent = PriceComparatorAgent(settings=get_settings(), tenant_id=auth.tenant_id)
    point = LiveKeyPoint(
        kind=KeyPointKind.PRICE,
        text=f"报价 ¥{request.price:.0f}",
        quote=request.title,
        confidence=0.9,
    )
    alert = await agent.check([point], request.title)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="比价失败，请稍后重试"
        )
    return ApiResponse(code=200, message="success", data=alert)


@router.websocket("/sessions/{session_id}/ws")
async def live_websocket(websocket: WebSocket, session_id: str) -> None:
    """直播实时推送。

    客户端发送::

        {"type": "batch", "segments": [...], "danmaku": [...], "current_product": "..."}

    服务端每次回推合并后的完整快照。

    Args:
        websocket: WebSocket 连接。
        session_id: 会话标识。
    """
    # 鉴权必须在 accept() 之前完成
    try:
        auth = authenticate_websocket(websocket)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="鉴权失败")
        return

    if not (auth.has_scope("*") or auth.has_scope("live:write")):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Forbidden")
        return

    await websocket.accept()

    try:
        payload = await _load_payload(session_id, auth.tenant_id)
    except HTTPException:
        await websocket.send_json({"error": "直播会话不存在"})
        await websocket.close()
        return

    if not payload:
        await websocket.send_json({"error": "会话暂无快照数据"})
        await websocket.close()
        return

    snapshot = LiveSnapshot.model_validate(payload)
    workflow = LiveWorkflow(settings=get_settings())
    await websocket.send_json(snapshot.model_dump(mode="json"))

    try:
        while True:
            raw = await websocket.receive_json()
            segments = [TranscriptSegment.model_validate(item) for item in raw.get("segments", [])]
            danmaku = [DanmakuItem.model_validate(item) for item in raw.get("danmaku", [])]

            if not segments and not danmaku:
                await websocket.send_json({"error": "本批次没有任何字幕或弹幕"})
                continue

            try:
                snapshot = await workflow.process(
                    session_id=session_id,
                    segments=segments,
                    danmaku=danmaku,
                    current_product=raw.get("current_product"),
                    snapshot=snapshot,
                    tenant_id=auth.tenant_id,
                )
                await _save_snapshot(session_id, auth.tenant_id, snapshot)
                await websocket.send_json(snapshot.model_dump(mode="json"))
            except Exception as exc:  # 单批失败不中断连接
                logger.warning("直播批次处理失败: %s", exc)
                await websocket.send_json({"error": f"批次处理失败: {exc}"})
    except WebSocketDisconnect:
        logger.info("直播 WebSocket 已断开: %s", session_id)
    except Exception as exc:  # 协议异常等
        logger.warning("直播 WebSocket 异常: %s", exc)
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
