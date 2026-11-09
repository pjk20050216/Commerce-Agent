"""
话术生成 Agent。

Description:
    根据事实与规则判定，生成三种可直接复制使用的文本：
    - 投诉：向平台投诉商家，要求介入处理
    - 申诉：对平台已有处理结果不服，申请复核
    - 协商：先与商家沟通，语气缓和、给出台阶与折中方案

    三种文本都遵循「事实 → 诉求 → 依据 → 证据」四段式，
    并只引用规则库中真实存在的条款，不凭空编造法条或金额。
2026-11-09
"""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentResult, AgentRole
from src.agents.consumer_base import ConsumerAgentBase
from src.graph.dispute_state import DisputeState
from src.models.dispute import (
    ArbitrationVerdict,
    ComplaintDraft,
    DisputeOrderInput,
    DraftTone,
    FactSheet,
    Responsibility,
)

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "以上内容由规则库与模型自动生成，仅供争议处理参考，不构成法律意见；"
    "具体责任认定与赔偿标准以平台规则及司法机关认定为准。"
)

TONE_LABEL: dict[DraftTone, str] = {
    DraftTone.COMPLAINT: "投诉",
    DraftTone.APPEAL: "申诉",
    DraftTone.NEGOTIATION: "协商",
}

RESPONSIBILITY_LABEL: dict[Responsibility, str] = {
    Responsibility.MERCHANT: "商家责任",
    Responsibility.CONSUMER: "消费者举证不足",
    Responsibility.PLATFORM: "平台责任",
    Responsibility.SHARED: "双方共担",
    Responsibility.UNDETERMINED: "责任待定",
}

NEXT_ACTIONS: dict[DraftTone, list[str]] = {
    DraftTone.COMPLAINT: [
        "在平台「申请客服介入 / 交易投诉」入口提交本段文字",
        "同时上传开箱视频、商品实拍与聊天记录截图",
        "保留物流面单与快递外包装照片，便于后续举证",
    ],
    DraftTone.APPEAL: [
        "在平台「申诉 / 复核」入口提交，并附上此前处理结果截图",
        "补充能推翻原判定的新证据（如检测报告、官方验真结果）",
        "平台 48 小时未响应可拨打 12315 或通过全国 12315 平台投诉",
    ],
    DraftTone.NEGOTIATION: [
        "先发给商家在线客服，避免一上来就升级为投诉",
        "明确提出可接受的方案区间（如全额退款 / 部分退款 / 补发）",
        "全程保留沟通记录，协商不成再走平台介入",
    ],
}


class NegotiatorAgent(ConsumerAgentBase[DisputeState]):
    """话术生成 Agent。

    Example:
        >>> agent = NegotiatorAgent(enable_llm=False)
        >>> drafts = await agent.write_drafts(order, sheet, verdict)
        >>> {draft.tone for draft in drafts} == {
        ...     DraftTone.COMPLAINT, DraftTone.APPEAL, DraftTone.NEGOTIATION}
        True
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化话术生成 Agent。

        Args:
            enable_llm: 是否允许 LLM 撰写正文。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.DISPUTE_NEGOTIATOR,
            enable_llm=enable_llm,
            **kwargs,
        )
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """注册提示模板。"""
        self.register_prompt(
            "draft",
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是一名擅长消费维权的沟通顾问。请写一段{tone}文本，要求：\n"
                        "1) 四段式结构：事实经过 / 我的诉求 / 依据 / 证据清单；\n"
                        "2) 语气{tone_style}，不谩骂、不威胁，不用感叹号堆砌情绪；\n"
                        "3) 只引用下面提供的条款原文，禁止编造法条、金额或平台规则；\n"
                        "4) 300 字以内，可直接复制发送。",
                    ),
                    (
                        "human",
                        "订单信息：{order}\n"
                        "事实时间线：\n{timeline}\n"
                        "关键事实：{facts}\n"
                        "责任判定：{responsibility}\n"
                        "可用条款：{clauses}\n"
                        "建议方案：{compensation}",
                    ),
                ]
            ),
        )

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    async def write_drafts(
        self,
        order: DisputeOrderInput,
        fact_sheet: FactSheet,
        verdict: ArbitrationVerdict,
        tones: list[DraftTone] | None = None,
    ) -> list[ComplaintDraft]:
        """生成话术。

        Args:
            order: 争议订单。
            fact_sheet: 事实清单。
            verdict: 裁决结果。
            tones: 需要生成的语气，缺省生成全部三种。

        Returns:
            话术草稿列表。
        """
        drafts: list[ComplaintDraft] = []
        for tone in tones or (DraftTone.COMPLAINT, DraftTone.APPEAL, DraftTone.NEGOTIATION):
            fallback = self._fallback_body(order, fact_sheet, verdict, tone)
            body = await self.try_generate(
                self.get_prompt("draft"),
                {
                    "tone": TONE_LABEL[tone],
                    "tone_style": self._tone_style(tone),
                    "order": self._format_order(order),
                    "timeline": self._format_timeline(fact_sheet),
                    "facts": "；".join(item.statement for item in fact_sheet.key_facts[:5]) or "无",
                    "responsibility": RESPONSIBILITY_LABEL[verdict.responsibility],
                    "clauses": "\n".join(verdict.legal_basis[:3]) or "暂无可引用条款",
                    "compensation": verdict.suggested_compensation,
                },
                accept=lambda text: len(text) >= 80,
            )

            drafts.append(
                ComplaintDraft(
                    tone=tone,
                    title=self._title(order, verdict, tone),
                    body=body or fallback,
                    cited_clauses=verdict.legal_basis[:3],
                    next_actions=NEXT_ACTIONS[tone],
                )
            )
        return drafts

    # ------------------------------------------------------------------
    # 文案
    # ------------------------------------------------------------------
    @staticmethod
    def _tone_style(tone: DraftTone) -> str:
        """返回语气的文字描述。

        Args:
            tone: 语气类型。

        Returns:
            描述文本。
        """
        return {
            DraftTone.COMPLAINT: "正式、客观、诉求明确",
            DraftTone.APPEAL: "克制、有理有据、强调程序",
            DraftTone.NEGOTIATION: "友好、留有余地、寻求双赢",
        }[tone]

    @staticmethod
    def _title(order: DisputeOrderInput, verdict: ArbitrationVerdict, tone: DraftTone) -> str:
        """生成话术标题。

        Args:
            order: 订单。
            verdict: 裁决。
            tone: 语气。

        Returns:
            标题文本。
        """
        product = order.product_title or "商品"
        if tone is DraftTone.COMPLAINT:
            return f"[投诉] 订单 {order.order_id} {product} 售后争议，请求平台介入"
        if tone is DraftTone.APPEAL:
            return f"[申诉] 订单 {order.order_id} 处理结果复核申请"
        return f"[协商] 订单 {order.order_id} 售后问题沟通"

    @staticmethod
    def _format_order(order: DisputeOrderInput) -> str:
        """格式化订单信息。

        Args:
            order: 订单。

        Returns:
            文本。
        """
        parts = [f"订单号 {order.order_id}", f"平台 {order.platform}"]
        if order.product_title:
            parts.append(f"商品 {order.product_title}")
        if order.amount:
            parts.append(f"金额 ¥{order.amount:.2f}")
        if order.paid_at:
            parts.append(f"下单时间 {order.paid_at:%Y-%m-%d %H:%M}")
        return "，".join(parts)

    @staticmethod
    def _format_timeline(fact_sheet: FactSheet) -> str:
        """格式化时间线。

        Args:
            fact_sheet: 事实清单。

        Returns:
            多行文本。
        """
        lines: list[str] = []
        for node in fact_sheet.timeline[:8]:
            stamp = f"{node.occurred_at:%Y-%m-%d %H:%M}" if node.occurred_at else "时间未知"
            detail = f"：{node.detail}" if node.detail else ""
            lines.append(f"- {stamp} {node.title}{detail}")
        return "\n".join(lines) if lines else "- 暂无时间线信息"

    def _fallback_body(
        self,
        order: DisputeOrderInput,
        fact_sheet: FactSheet,
        verdict: ArbitrationVerdict,
        tone: DraftTone,
    ) -> str:
        """规则版话术正文（LLM 不可用时使用）。

        Args:
            order: 订单。
            fact_sheet: 事实清单。
            verdict: 裁决。
            tone: 语气。

        Returns:
            正文文本。
        """
        opening = {
            DraftTone.COMPLAINT: "平台客服您好，现就以下订单的售后问题申请平台介入：",
            DraftTone.APPEAL: "平台客服您好，我对该订单此前的处理结果存在异议，现申请复核：",
            DraftTone.NEGOTIATION: "您好，关于这笔订单想和您沟通一下，希望能协商解决：",
        }[tone]

        facts_lines = [
            f"{index}. {item.statement}"
            for index, item in enumerate(fact_sheet.key_facts[:4], start=1)
        ]
        clauses = "\n".join(f"- {item}" for item in verdict.legal_basis[:3]) or "- 暂无"
        evidence = "\n".join(
            f"- {item.title}：{item.content[:60]}" for item in fact_sheet.evidence[:5]
        )

        demand = {
            DraftTone.COMPLAINT: verdict.suggested_compensation,
            DraftTone.APPEAL: f"请重新审核本次处理结果，{verdict.suggested_compensation}",
            DraftTone.NEGOTIATION: (
                f"{verdict.suggested_compensation}"
                "如您有更合适的处理方式，也欢迎提出。"
            ),
        }[tone]

        return (
            f"{opening}\n\n"
            f"【订单】{self._format_order(order)}\n\n"
            f"【事实经过】\n" + ("\n".join(facts_lines) or "1. 争议事实尚待补充") + "\n\n"
            f"【我的诉求】\n{demand}\n\n"
            f"【依据】\n{clauses}\n\n"
            f"【证据】\n" + (evidence or "- 暂无") + "\n\n"
            f"请予处理，谢谢。"
        )

    async def execute(self, state: DisputeState) -> AgentResult:
        """生成话术（工作流节点接口）。

        Args:
            state: 仲裁庭状态。

        Returns:
            包含话术草稿的结果对象。
        """
        try:
            if state.fact_sheet is None or state.verdict is None:
                return AgentResult(success=False, error="缺少事实或裁决结果，无法生成话术")

            drafts = await self.write_drafts(state.order, state.fact_sheet, state.verdict)
            return AgentResult(
                success=True,
                data={"drafts": [draft.model_dump(mode="json") for draft in drafts]},
            )
        except Exception as exc:
            logger.exception("话术生成失败")
            return AgentResult(success=False, error=f"话术生成失败: {exc}")
