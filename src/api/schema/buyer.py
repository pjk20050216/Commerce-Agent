"""
虚拟买手团 API Schema。

Description:
    定义买手决策卡的请求/响应 DTO。2026-11-09
"""

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.buyer import (
    BrowsingRecord,
    CandidateProduct,
    Recommendation,
)


class BuyerDecisionRequest(BaseModel):
    """生成买手决策卡的请求。"""

    user_id: str = Field(..., min_length=1, max_length=100, description="用户标识")
    candidate: CandidateProduct = Field(..., description="候选商品")
    history: list[BrowsingRecord] = Field(
        default_factory=list, description="用户历史浏览/收藏/加购/购买记录"
    )
    persist: bool = Field(default=True, description="是否落库保存")


class BuyerDecisionSummary(BaseModel):
    """决策卡列表项。"""

    card_id: str = Field(..., description="决策卡标识")
    user_id: str = Field(..., description="用户标识")
    title: str = Field(..., description="商品标题")
    overall_score: float = Field(..., description="综合评分")
    recommendation: Recommendation = Field(..., description="建议档位")
    is_mock_data: bool = Field(default=False, description="是否包含模拟外部数据")
    created_at: datetime | None = Field(default=None, description="创建时间")


class PriceCompareRequest(BaseModel):
    """单独发起全网比价的请求。"""

    title: str = Field(..., min_length=1, max_length=300, description="商品标题")
    current_price: float | None = Field(
        default=None, ge=0, description="当前价格，缺省取全网最低价"
    )
    history_days: int | None = Field(
        default=None, ge=1, le=365, description="历史价格回看天数"
    )
