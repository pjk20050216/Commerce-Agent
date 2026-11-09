"""
售后纠纷仲裁庭工作流构建器。

Description:
    三段式串行流水线::

        START ─▶ FactRestorer ─▶ RuleInterpreter ─▶ Negotiator ─▶ END

    之所以不并行：规则解读依赖事实标记，话术撰写依赖裁决结论，
    任何一步的输出都是下一步的输入。
2026-11-09
"""

import logging
import uuid
from typing import Any

from langgraph.graph import END, StateGraph

from src.agents.dispute_fact_restorer import FactRestorerAgent
from src.agents.dispute_negotiator import DISCLAIMER, NegotiatorAgent
from src.agents.dispute_rule_interpreter import RuleInterpreterAgent
from src.graph.dispute_state import DisputeState
from src.models.dispute import (
    ArbitrationVerdict,
    ChatMessageInput,
    ComplaintDraft,
    DisputeCaseResult,
    DisputeOrderInput,
    FactSheet,
    LogisticsEventInput,
    UnboxingEvidence,
)

logger = logging.getLogger(__name__)


class DisputeTribunalWorkflow:
    """售后纠纷仲裁庭工作流。

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
        self._builder = StateGraph(DisputeState)
        self._build_graph()
        # 不挂 MemorySaver：状态由调用方完整传入并原样返回，
        # 挂 checkpointer 只会引入 msgpack 序列化 Pydantic 模型的告警，
        # 且复用 thread_id 时容易读到上一轮的陈旧状态。
        self.app = self._builder.compile()

    def _build_graph(self) -> None:
        """构建状态图。"""
        self._builder.add_node("fact_restorer", self._fact_node)
        self._builder.add_node("rule_interpreter", self._rule_node)
        self._builder.add_node("negotiator", self._draft_node)

        self._builder.set_entry_point("fact_restorer")
        self._builder.add_edge("fact_restorer", "rule_interpreter")
        self._builder.add_edge("rule_interpreter", "negotiator")
        self._builder.add_edge("negotiator", END)

    def _agent_kwargs(self, state: DisputeState) -> dict[str, Any]:
        """构造 Agent 公共参数。

        Args:
            state: 仲裁庭状态。

        Returns:
            关字参数。
        """
        return {
            "enable_llm": self._enable_llm,
            "settings": self._settings,
            "tenant_id": state.tenant_id or "system",
        }

    async def _fact_node(self, state: DisputeState) -> dict[str, Any]:
        """事实还原节点。"""
        agent = FactRestorerAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {"error": result.error, "current_step": "fact_failed"}
        return {
            "fact_sheet": FactSheet.model_validate(result.data["fact_sheet"]),
            "facts": result.data["facts"],
            "current_step": "facts_restored",
        }

    async def _rule_node(self, state: DisputeState) -> dict[str, Any]:
        """规则解读节点。"""
        agent = RuleInterpreterAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {"error": result.error, "current_step": "rule_failed"}
        return {
            "verdict": ArbitrationVerdict.model_validate(result.data["verdict"]),
            "current_step": "rules_interpreted",
        }

    async def _draft_node(self, state: DisputeState) -> dict[str, Any]:
        """话术生成节点。"""
        agent = NegotiatorAgent(**self._agent_kwargs(state))
        result = await agent.execute(state)
        if not result.success:
            return {"error": result.error, "current_step": "draft_failed"}
        return {
            "drafts": [
                ComplaintDraft.model_validate(item) for item in result.data["drafts"]
            ],
            "current_step": "drafts_written",
        }

    async def run(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput] | None = None,
        logistics: list[LogisticsEventInput] | None = None,
        unboxing: list[UnboxingEvidence] | None = None,
        claim_text: str = "",
        tenant_id: str = "",
        case_id: str | None = None,
        thread_id: str | None = None,
    ) -> DisputeState:
        """执行仲裁庭工作流。

        Args:
            order: 争议订单。
            chat_log: 聊天记录。
            logistics: 物流轨迹。
            unboxing: 开箱凭证。
            claim_text: 用户诉求。
            tenant_id: 租户 ID。
            case_id: 案件编号，缺省自动生成。
            thread_id: 会话线程 ID，缺省自动生成。

        Returns:
            执行结束后的状态。
        """
        initial = DisputeState(
            case_id=case_id or f"case_{uuid.uuid4().hex[:10]}",
            order=order,
            chat_log=chat_log or [],
            logistics=logistics or [],
            unboxing=unboxing or [],
            claim_text=claim_text,
            tenant_id=tenant_id,
        )
        config = {"configurable": {"thread_id": thread_id or f"dispute-{uuid.uuid4().hex[:8]}"}}
        result = await self.app.ainvoke(initial, config=config)
        if isinstance(result, DisputeState):
            return result
        return DisputeState.model_validate(result)

    async def run_case(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput] | None = None,
        logistics: list[LogisticsEventInput] | None = None,
        unboxing: list[UnboxingEvidence] | None = None,
        claim_text: str = "",
        tenant_id: str = "",
    ) -> DisputeCaseResult:
        """执行工作流并返回完整案件结果。

        Args:
            order: 争议订单。
            chat_log: 聊天记录。
            logistics: 物流轨迹。
            unboxing: 开箱凭证。
            claim_text: 用户诉求。
            tenant_id: 租户 ID。

        Returns:
            案件结果。

        Raises:
            RuntimeError: 未能产出裁决。
        """
        state = await self.run(
            order=order,
            chat_log=chat_log,
            logistics=logistics,
            unboxing=unboxing,
            claim_text=claim_text,
            tenant_id=tenant_id,
        )
        if state.verdict is None or state.fact_sheet is None:
            raise RuntimeError(state.error or "仲裁庭未能给出裁决")

        return DisputeCaseResult(
            case_id=state.case_id,
            order_id=order.order_id,
            verdict=state.verdict,
            fact_sheet=state.fact_sheet,
            drafts=state.drafts,
            disclaimer=DISCLAIMER,
        )
