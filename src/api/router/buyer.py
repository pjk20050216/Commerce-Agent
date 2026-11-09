"""
虚拟买手团 API 路由。

Description:
    提供买手决策卡生成、历史查询与独立比价接口。
    决策流程由 LangGraph 三路并行 Agent 完成，接口同步返回结果并落库。2026-11-09
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from src.agents.buyer_value_analyst import ValueAnalystAgent
from src.api.deps import AuthDep
from src.api.schema.buyer import (
    BuyerDecisionRequest,
    BuyerDecisionSummary,
    PriceCompareRequest,
)
from src.api.schema.common import ApiResponse
from src.config.settings import get_settings
from src.db.consumer_models import BuyerDecisionCardPO
from src.db.postgres import get_db_session
from src.db.repository import TenantRepository
from src.graph.buyer_workflow import BuyerTeamWorkflow
from src.models.buyer import BuyerDecisionCard, CandidateProduct, PriceComparison

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


def _to_summary(po: BuyerDecisionCardPO) -> BuyerDecisionSummary:
    """把 ORM 记录转换为列表项。

    Args:
        po: 决策卡记录。

    Returns:
        列表项。
    """
    return BuyerDecisionSummary(
        card_id=po.card_id,
        user_id=po.user_id,
        title=po.title,
        overall_score=po.overall_score,
        recommendation=po.recommendation,  # type: ignore[arg-type]
        is_mock_data=bool((po.payload or {}).get("is_mock_data", False)),
        created_at=po.created_at,
    )


@router.post(
    "/decisions",
    response_model=ApiResponse[BuyerDecisionCard],
    summary="生成买手决策卡",
)
async def create_decision(
    request: BuyerDecisionRequest,
    auth: AuthDep,
) -> ApiResponse[BuyerDecisionCard]:
    """运行虚拟买手团，生成一张买手决策卡。

    Args:
        request: 决策请求。
        auth: 认证上下文。

    Returns:
        买手决策卡。
    """
    _ensure_enabled()

    workflow = BuyerTeamWorkflow(settings=get_settings())
    try:
        card = await workflow.run_card(
            user_id=request.user_id,
            candidate=request.candidate,
            history=request.history,
            tenant_id=auth.tenant_id,
        )
    except RuntimeError as exc:
        logger.warning("买手团决策失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"买手团决策失败: {exc}",
        ) from exc

    if request.persist:
        try:
            async with get_db_session() as session:
                repo = TenantRepository(BuyerDecisionCardPO, session)
                await repo.create_for_tenant(
                    auth.tenant_id,
                    user_id=card.user_id,
                    card_id=card.card_id,
                    title=card.candidate.title,
                    overall_score=card.score.overall,
                    recommendation=card.recommendation.value,
                    payload=card.model_dump(mode="json"),
                )
        except Exception as exc:  # 落库失败不影响本次结果返回
            logger.warning("决策卡落库失败: %s", exc)

    return ApiResponse(code=200, message="决策卡生成成功", data=card)


@router.get(
    "/decisions",
    response_model=ApiResponse[list[BuyerDecisionSummary]],
    summary="决策卡历史",
)
async def list_decisions(
    auth: AuthDep,
    user_id: str | None = Query(default=None, description="按用户过滤"),
    limit: int = Query(default=20, ge=1, le=100, description="返回条数"),
) -> ApiResponse[list[BuyerDecisionSummary]]:
    """查询当前租户的决策卡历史。

    Args:
        auth: 认证上下文。
        user_id: 可选的用户过滤。
        limit: 返回条数。

    Returns:
        决策卡列表项。
    """
    _ensure_enabled()

    async with get_db_session() as session:
        repo = TenantRepository(BuyerDecisionCardPO, session)
        filters = {"user_id": user_id} if user_id else {}
        records = await repo.list_for_tenant(auth.tenant_id, **filters)

    ordered = sorted(
        records,
        key=lambda item: item.created_at or datetime.min,
        reverse=True,
    )[:limit]
    return ApiResponse(
        code=200,
        message="success",
        data=[_to_summary(item) for item in ordered],
    )


@router.get(
    "/decisions/{card_id}",
    response_model=ApiResponse[BuyerDecisionCard],
    summary="决策卡详情",
)
async def get_decision(card_id: str, auth: AuthDep) -> ApiResponse[BuyerDecisionCard]:
    """按 card_id 获取决策卡详情。

    Args:
        card_id: 决策卡标识。
        auth: 认证上下文。

    Returns:
        买手决策卡。

    Raises:
        HTTPException: 记录不存在时返回 404。
    """
    _ensure_enabled()

    async with get_db_session() as session:
        stmt = select(BuyerDecisionCardPO).where(
            BuyerDecisionCardPO.tenant_id == auth.tenant_id,
            BuyerDecisionCardPO.card_id == card_id,
        )
        record = (await session.execute(stmt)).scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="决策卡不存在")

    return ApiResponse(
        code=200,
        message="success",
        data=BuyerDecisionCard.model_validate(record.payload),
    )


@router.post(
    "/compare",
    response_model=ApiResponse[PriceComparison],
    summary="全网比价",
)
async def compare_price(
    request: PriceCompareRequest,
    auth: AuthDep,
) -> ApiResponse[PriceComparison]:
    """单独发起一次全网比价（不进决策流程）。

    Args:
        request: 比价请求。
        auth: 认证上下文。

    Returns:
        比价结果。
    """
    _ensure_enabled()

    analyst = ValueAnalystAgent(settings=get_settings(), tenant_id=auth.tenant_id)
    candidate = CandidateProduct(
        title=request.title,
        price=request.current_price or 0.0,
    )
    comparison = await analyst.compare(
        candidate,
        history_days=request.history_days,
        current_price=request.current_price,
    )
    return ApiResponse(code=200, message="success", data=comparison)
