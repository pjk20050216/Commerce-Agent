"""
虚拟买手团工作流构建器。

Description:
    基于 LangGraph StateGraph 构建「三路并行 → 汇总决策」的买手团流程::

        START ─┬─▶ StyleAdvisor ────┐
               ├─▶ ValueAnalyst ────┼─▶ DecisionMaker ─▶ END
               └─▶ QualityInspector ┘

    三路互不依赖，因此并行执行：比价要等外部数据源，质检是本地计算，
    并行可以把整体耗时压到最慢那一路。
2026-11-09
"""

import logging
import uuid
from typing import Any

from langgraph.graph import END, StateGraph

from src.agents.buyer_decision_maker import DecisionMakerAgent
from src.agents.buyer_quality_inspector import QualityInspectorAgent
from src.agents.buyer_style_advisor import StyleAdvisorAgent
from src.agents.buyer_value_analyst import ValueAnalystAgent
from src.graph.buyer_state import BuyerState
from src.models.buyer import (
    AgentTraceItem,
    BrowsingRecord,
    BuyerDecisionCard,
    CandidateProduct,
    PriceComparison,
    QualityAssessment,
    StyleProfile,
)

logger = logging.getLogger(__name__)


class BuyerTeamWorkflow:
    """虚拟买手团工作流。

    Attributes:
        app: 编译后的 LangGraph 应用。
    """

    def __init__(self, settings: Any | None = None, enable_llm: bool = True) -> None:
        """初始化工作流。

        Args:
            settings: 可选配置对象。
            enable_llm: 是否允许各 Agent 调用 LLM 增强。
        """
        self._settings = settings
        self._enable_llm = enable_llm
        self._builder = StateGraph(BuyerState)
        self._build_graph()
        # 不挂 MemorySaver：状态由调用方完整传入并原样返回，
        # 挂 checkpointer 只会引入 msgpack 序列化 Pydantic 模型的告警，
        # 且复用 thread_id 时容易读到上一轮的陈旧状态。
        self.app = self._builder.compile()

    def _build_graph(self) -> None:
        """构建状态图。"""
        self._builder.add_node("prepare", self._prepare_node)
        self._builder.add_node("style_advisor", self._style_node)
        self._builder.add_node("value_analyst", self._value_node)
        self._builder.add_node("quality_inspector", self._quality_node)
        self._builder.add_node("decision_maker", self._decide_node)

        # prepare 只是并行分发点：三路 Agent 同时启动
        self._builder.set_entry_point("prepare")
        self._builder.add_edge("prepare", "style_advisor")
        self._builder.add_edge("prepare", "value_analyst")
        self._builder.add_edge("prepare", "quality_inspector")
        self._builder.add_edge("style_advisor", "decision_maker")
        self._builder.add_edge("value_analyst", "decision_maker")
        self._builder.add_edge("quality_inspector", "decision_maker")
        self._builder.add_edge("decision_maker", END)

    async def _prepare_node(self, state: BuyerState) -> dict[str, Any]:
        """分发节点（无业务逻辑）。

        Args:
            state: 买手团状态。

        Returns:
            空更新。
        """
        return {"current_step": "dispatched"}

    # ------------------------------------------------------------------
    # 节点
    # ------------------------------------------------------------------
    def _agent_kwargs(self, state: BuyerState) -> dict[str, Any]:
        """构造 Agent 公共参数。

        Args:
            state: 买手团状态。

        Returns:
            关字参数。
        """
        return {
            "enable_llm": self._enable_llm,
            "settings": self._settings,
            "tenant_id": state.tenant_id or "system",
        }

    async def _style_node(self, state: BuyerState) -> dict[str, Any]:
        """风格顾问节点。"""
        agent = StyleAdvisorAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {
                "error": result.error,
                "agent_trace": [
                    AgentTraceItem(
                        agent="buyer_style_advisor",
                        status="failed",
                        detail=result.error or "",
                    )
                ],
            }
        payload = result.data
        return {
            "style_profile": StyleProfile.model_validate(payload["style_profile"]),
            "style_fit": payload["style_fit"],
            "style_reasons": payload["style_reasons"],
            "agent_trace": [AgentTraceItem.model_validate(payload["agent_trace"])],
        }

    async def _value_node(self, state: BuyerState) -> dict[str, Any]:
        """性价比分析师节点。"""
        agent = ValueAnalystAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {
                "error": result.error,
                "agent_trace": [
                    AgentTraceItem(
                        agent="buyer_value_analyst",
                        status="failed",
                        detail=result.error or "",
                    )
                ],
            }
        payload = result.data
        return {
            "price_comparison": PriceComparison.model_validate(payload["price_comparison"]),
            "agent_trace": [AgentTraceItem.model_validate(payload["agent_trace"])],
        }

    async def _quality_node(self, state: BuyerState) -> dict[str, Any]:
        """质检员节点。"""
        agent = QualityInspectorAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {
                "error": result.error,
                "agent_trace": [
                    AgentTraceItem(
                        agent="buyer_quality_inspector",
                        status="failed",
                        detail=result.error or "",
                    )
                ],
            }
        payload = result.data
        return {
            "quality": QualityAssessment.model_validate(payload["quality"]),
            "agent_trace": [AgentTraceItem.model_validate(payload["agent_trace"])],
        }

    async def _decide_node(self, state: BuyerState) -> dict[str, Any]:
        """决策官节点。"""
        agent = DecisionMakerAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {"error": result.error, "current_step": "decision_failed"}
        payload = result.data
        return {
            "card": BuyerDecisionCard.model_validate(payload["card"]),
            "current_step": "decided",
        }

    # ------------------------------------------------------------------
    # 对外入口
    # ------------------------------------------------------------------
    async def run(
        self,
        user_id: str,
        candidate: CandidateProduct,
        history: list[BrowsingRecord] | None = None,
        tenant_id: str = "",
        thread_id: str | None = None,
    ) -> BuyerState:
        """执行买手团工作流。

        Args:
            user_id: 用户 ID。
            candidate: 候选商品。
            history: 用户历史行为。
            tenant_id: 租户 ID。
            thread_id: 会话线程 ID，缺省自动生成。

        Returns:
            执行结束后的状态。
        """
        initial = BuyerState(
            user_id=user_id,
            candidate=candidate,
            history=history or [],
            tenant_id=tenant_id,
        )
        config = {"configurable": {"thread_id": thread_id or f"buyer-{uuid.uuid4().hex[:8]}"}}
        result = await self.app.ainvoke(initial, config=config)
        if isinstance(result, BuyerState):
            return result
        return BuyerState.model_validate(result)

    async def run_card(
        self,
        user_id: str,
        candidate: CandidateProduct,
        history: list[BrowsingRecord] | None = None,
        tenant_id: str = "",
    ) -> BuyerDecisionCard:
        """执行工作流并直接返回决策卡。

        Args:
            user_id: 用户 ID。
            candidate: 候选商品。
            history: 用户历史行为。
            tenant_id: 租户 ID。

        Returns:
            买手决策卡。

        Raises:
            RuntimeError: 工作流未产出决策卡。
        """
        state = await self.run(
            user_id=user_id,
            candidate=candidate,
            history=history,
            tenant_id=tenant_id,
        )
        if state.card is None:
            raise RuntimeError(state.error or "买手团未能生成决策卡")
        return state.card
