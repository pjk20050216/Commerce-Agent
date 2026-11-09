"""
售后纠纷仲裁庭 API 路由。

Description:
    提供案件受理、历史查询与话术重生成接口。
    仲裁流程由 LangGraph 三阶段串行 Agent 完成：事实还原 → 规则解读 → 话术生成。2026-11-09
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from src.agents.dispute_negotiator import NegotiatorAgent
from src.api.deps import AuthDep
from src.api.schema.common import ApiResponse
from src.api.schema.dispute import (
    DisputeCaseRequest,
    DisputeCaseSummary,
    RegenerateDraftRequest,
)
from src.config.settings import get_settings
from src.db.consumer_models import DisputeCasePO
from src.db.postgres import get_db_session
from src.db.repository import TenantRepository
from src.graph.dispute_workflow import DisputeTribunalWorkflow
from src.models.dispute import (
    ComplaintDraft,
    DisputeCaseResult,
    Responsibility,
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


def _to_summary(po: DisputeCasePO) -> DisputeCaseSummary:
    """把 ORM 记录转换为列表项。

    Args:
        po: 案件记录。

    Returns:
        列表项。
    """
    return DisputeCaseSummary(
        case_id=po.case_id,
        order_id=po.order_id,
        platform=po.platform,
        responsibility=po.responsibility,  # type: ignore[arg-type]
        confidence=po.confidence,
        created_at=po.created_at,
    )


async def _load_case(case_id: str, tenant_id: str) -> DisputeCasePO:
    """读取指定租户下的案件记录。

    Args:
        case_id: 案件编号。
        tenant_id: 租户 ID。

    Returns:
        案件记录。

    Raises:
        HTTPException: 记录不存在时返回 404。
    """
    async with get_db_session() as session:
        stmt = select(DisputeCasePO).where(
            DisputeCasePO.tenant_id == tenant_id,
            DisputeCasePO.case_id == case_id,
        )
        record = (await session.execute(stmt)).scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案件不存在")
    return record


@router.post(
    "/cases",
    response_model=ApiResponse[DisputeCaseResult],
    summary="提交纠纷仲裁",
)
async def create_case(
    request: DisputeCaseRequest,
    auth: AuthDep,
) -> ApiResponse[DisputeCaseResult]:
    """受理纠纷并给出仲裁结论与话术。

    Args:
        request: 仲裁请求。
        auth: 认证上下文。

    Returns:
        案件结果。
    """
    _ensure_enabled()

    workflow = DisputeTribunalWorkflow(settings=get_settings())
    try:
        result = await workflow.run_case(
            order=request.order,
            chat_log=request.chat_log,
            logistics=request.logistics,
            unboxing=request.unboxing,
            claim_text=request.claim_text,
            tenant_id=auth.tenant_id,
        )
    except RuntimeError as exc:
        logger.warning("纠纷仲裁失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"纠纷仲裁失败: {exc}",
        ) from exc

    if request.persist:
        try:
            async with get_db_session() as session:
                repo = TenantRepository(DisputeCasePO, session)
                await repo.create_for_tenant(
                    auth.tenant_id,
                    case_id=result.case_id,
                    order_id=result.order_id,
                    platform=request.order.platform,
                    responsibility=result.verdict.responsibility.value,
                    confidence=result.verdict.confidence,
                    payload=result.model_dump(mode="json"),
                )
        except Exception as exc:  # 落库失败不影响本次结果返回
            logger.warning("案件落库失败: %s", exc)

    return ApiResponse(code=200, message="仲裁完成", data=result)


@router.get(
    "/cases",
    response_model=ApiResponse[list[DisputeCaseSummary]],
    summary="案件历史",
)
async def list_cases(
    auth: AuthDep,
    responsibility: Responsibility | None = Query(default=None, description="按责任方过滤"),
    limit: int = Query(default=20, ge=1, le=100, description="返回条数"),
) -> ApiResponse[list[DisputeCaseSummary]]:
    """查询当前租户的仲裁案件。

    Args:
        auth: 认证上下文。
        responsibility: 可选的责任方过滤。
        limit: 返回条数。

    Returns:
        案件列表项。
    """
    _ensure_enabled()

    async with get_db_session() as session:
        repo = TenantRepository(DisputeCasePO, session)
        filters = {"responsibility": responsibility.value} if responsibility else {}
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
    "/cases/{case_id}",
    response_model=ApiResponse[DisputeCaseResult],
    summary="案件详情",
)
async def get_case(case_id: str, auth: AuthDep) -> ApiResponse[DisputeCaseResult]:
    """按 case_id 获取案件详情。

    Args:
        case_id: 案件编号。
        auth: 认证上下文。

    Returns:
        案件结果。
    """
    _ensure_enabled()

    record = await _load_case(case_id, auth.tenant_id)
    return ApiResponse(
        code=200,
        message="success",
        data=DisputeCaseResult.model_validate(record.payload),
    )


@router.post(
    "/cases/{case_id}/draft",
    response_model=ApiResponse[ComplaintDraft],
    summary="重新生成话术",
)
async def regenerate_draft(
    case_id: str,
    request: RegenerateDraftRequest,
    auth: AuthDep,
) -> ApiResponse[ComplaintDraft]:
    """按指定语气重新生成话术。

    Args:
        case_id: 案件编号。
        request: 语气参数。
        auth: 认证上下文。

    Returns:
        单条话术草稿。
    """
    _ensure_enabled()

    record = await _load_case(case_id, auth.tenant_id)
    result = DisputeCaseResult.model_validate(record.payload)

    agent = NegotiatorAgent(settings=get_settings(), tenant_id=auth.tenant_id)
    drafts = await agent.write_drafts(
        order=result.fact_sheet.order,
        fact_sheet=result.fact_sheet,
        verdict=result.verdict,
        tones=[request.tone],
    )
    if not drafts:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="话术生成失败",
        )

    return ApiResponse(code=200, message="success", data=drafts[0])
