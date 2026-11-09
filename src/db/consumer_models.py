"""
消费者侧数据库模型。

Description:
    持久化三类产物：
    - 买手决策卡（buyer_decision_cards）
    - 纠纷仲裁案件（dispute_cases）
    - 直播会话快照（live_sessions）

    统一用 JSONB 存完整结果、把可查询字段（评分、责任方、状态）单独提列，
    这样既能按字段筛选，又能直接把完整结构还原成 Pydantic 模型。
2026-11-09
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.postgres import Base


def utcnow() -> datetime:
    """获取不带时区的 UTC 时间。

    项目既有表统一用「naive UTC」存时间，这里保持一致；
    直接调用 `datetime.utcnow()` 在 3.12+ 会触发弃用告警，故统一收敛到这个函数。

    Returns:
        当前 UTC 时间（naive）。
    """
    return datetime.now(UTC).replace(tzinfo=None)


class BuyerDecisionCardPO(Base):
    """买手决策卡表。

    Attributes:
        id: 主键。
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        card_id: 决策卡业务标识。
        title: 候选商品标题。
        overall_score: 综合评分。
        recommendation: 建议档位。
        payload: 完整决策卡 JSON。
        created_at: 创建时间。
    """

    __tablename__ = "buyer_decision_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="租户 ID"
    )
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    card_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    recommendation: Mapped[str] = mapped_column(String(32), default="consider")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("uq_buyer_cards_tenant_card", "tenant_id", "card_id", unique=True),
        Index("ix_buyer_cards_tenant_user", "tenant_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<BuyerDecisionCardPO(card_id='{self.card_id}', score={self.overall_score})>"


class DisputeCasePO(Base):
    """纠纷仲裁案件表。

    Attributes:
        id: 主键。
        tenant_id: 租户 ID。
        case_id: 案件业务标识。
        order_id: 订单号。
        platform: 平台。
        responsibility: 责任方。
        confidence: 判定置信度。
        payload: 完整案件结果 JSON。
        created_at: 创建时间。
    """

    __tablename__ = "dispute_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="租户 ID"
    )
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), default="unknown")
    responsibility: Mapped[str] = mapped_column(String(32), default="undetermined")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("uq_dispute_cases_tenant_case", "tenant_id", "case_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<DisputeCasePO(case_id='{self.case_id}', responsibility='{self.responsibility}')>"


class LiveSessionPO(Base):
    """直播会话表。

    Attributes:
        id: 主键。
        tenant_id: 租户 ID。
        session_id: 会话业务标识。
        room_id: 直播间标识。
        title: 直播标题。
        status: 状态（running/ended）。
        payload: 最新快照 JSON。
        created_at: 创建时间。
        updated_at: 更新时间。
        ended_at: 结束时间。
    """

    __tablename__ = "live_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="租户 ID"
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    room_id: Mapped[str] = mapped_column(String(100), default="")
    title: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("uq_live_sessions_tenant_session", "tenant_id", "session_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<LiveSessionPO(session_id='{self.session_id}', status='{self.status}')>"
