"""
事实还原 Agent。

Description:
    把散落的聊天记录、物流轨迹、开箱凭证整理成一条可读的时间线，
    并从中抽取「是否签收、签收几天、是否拆封、是否主张质量问题」等事实标记，
    供规则匹配使用。

    证据缺口同样重要：判定为「证据不足」比给出一个没有依据的结论更负责。
2026-11-09
"""

import logging
from datetime import datetime
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentResult, AgentRole
from src.agents.consumer_base import ConsumerAgentBase
from src.agents.dispute_rules import KEYWORD_FACTS
from src.graph.dispute_state import DisputeState
from src.models.dispute import (
    ChatMessageInput,
    DisputeOrderInput,
    EvidenceItem,
    EvidenceType,
    FactSheet,
    KeyFact,
    LogisticsEventInput,
    Speaker,
    TimelineNode,
    UnboxingEvidence,
)

logger = logging.getLogger(__name__)

SPEAKER_LABEL: dict[Speaker, str] = {
    Speaker.CONSUMER: "消费者",
    Speaker.MERCHANT: "商家",
    Speaker.PLATFORM: "平台客服",
    Speaker.SYSTEM: "系统",
}

# 物流状态 → 时间线阶段
LOGISTICS_PHASE = (
    ("揽收", "发货"),
    ("发货", "发货"),
    ("运输", "运输"),
    ("派送", "运输"),
    ("签收", "签收"),
    ("退回", "售后"),
)

# 需要「开箱影像」支撑的事实
IMAGE_BACKED_FACTS = ("quality_issue", "damage_on_arrival", "description_mismatch")


class FactRestorerAgent(ConsumerAgentBase[DisputeState]):
    """事实还原 Agent。

    Example:
        >>> restorer = FactRestorerAgent(enable_llm=False)
        >>> sheet, facts = await restorer.restore(order, chat, logistics, unboxing, claim)
        >>> facts["received"]
        True
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化事实还原 Agent。

        Args:
            enable_llm: 是否允许 LLM 生成事实摘要。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.DISPUTE_FACT_RESTORER,
            enable_llm=enable_llm,
            **kwargs,
        )
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """注册提示模板。"""
        self.register_prompt(
            "summary",
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是一名严谨的争议事实梳理员。根据给定时间线与关键事实，"
                        "用不超过 80 字的中文客观复述争议经过（谁在什么时间做了什么），"
                        "不做责任判断，不编造未出现的细节。",
                    ),
                    (
                        "human",
                        "时间线：\n{timeline}\n\n关键事实：\n{facts}\n\n证据缺口：\n{gaps}",
                    ),
                ]
            ),
        )

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    async def restore(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput] | None = None,
        logistics: list[LogisticsEventInput] | None = None,
        unboxing: list[UnboxingEvidence] | None = None,
        claim_text: str = "",
    ) -> tuple[FactSheet, dict[str, bool]]:
        """还原事实。

        Args:
            order: 争议订单。
            chat_log: 聊天记录。
            logistics: 物流轨迹。
            unboxing: 开箱凭证。
            claim_text: 用户诉求原文。

        Returns:
            ``(事实清单, 事实标记)`` 二元组。
        """
        chat_log = chat_log or []
        logistics = logistics or []
        unboxing = unboxing or []

        evidence = self._normalize_evidence(order, chat_log, logistics, unboxing)
        timeline = self._build_timeline(order, chat_log, logistics, unboxing)
        context = self._context_text(order, chat_log, logistics, unboxing, claim_text)
        facts = self._derive_facts(order, chat_log, logistics, unboxing, context)
        received_at = self._received_at(order, logistics)
        days_since_receipt = self._days_since(received_at)

        key_facts = self._build_key_facts(facts, days_since_receipt, received_at)
        gaps = self._find_gaps(facts, chat_log, unboxing, received_at)
        sheet = FactSheet(
            order=order,
            evidence=evidence,
            timeline=timeline,
            key_facts=key_facts,
            evidence_gaps=gaps,
            complete=not gaps,
            summary=self._rule_summary(timeline, key_facts, gaps, days_since_receipt),
        )

        corroborated = await self.try_generate(
            self.get_prompt("summary"),
            {
                "timeline": self._format_timeline(timeline),
                "facts": "\n".join(f"- {item.statement}" for item in key_facts) or "无",
                "gaps": "、".join(gaps) or "无",
            },
            accept=lambda text: 8 <= len(text) <= 200,
        )
        if corroborated:
            sheet.summary = corroborated

        return sheet, facts

    # ------------------------------------------------------------------
    # 证据归一化
    # ------------------------------------------------------------------
    def _normalize_evidence(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
        unboxing: list[UnboxingEvidence],
    ) -> list[EvidenceItem]:
        """把各类原始输入归一化为统一证据项。

        Args:
            order: 订单。
            chat_log: 聊天记录。
            logistics: 物流轨迹。
            unboxing: 开箱凭证。

        Returns:
            证据列表，编号从 E1 递增。
        """
        evidence: list[EvidenceItem] = [
            EvidenceItem(
                evidence_id="E1",
                type=EvidenceType.ORDER,
                title=f"订单 {order.order_id}",
                content=(
                    f"{order.platform} / {order.product_title or '商品'} / "
                    f"金额 ¥{order.amount:.2f}"
                ),
                occurred_at=order.paid_at,
                weight=0.9,
            )
        ]

        counter = 2
        for message in chat_log:
            label = SPEAKER_LABEL.get(message.speaker, "未知")
            evidence.append(
                EvidenceItem(
                    evidence_id=f"E{counter}",
                    type=EvidenceType.CHAT,
                    title=f"聊天记录 · {label}",
                    content=message.content,
                    occurred_at=message.sent_at,
                    weight=0.7 if message.speaker is Speaker.MERCHANT else 0.5,
                )
            )
            counter += 1

        for event in logistics:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"E{counter}",
                    type=EvidenceType.LOGISTICS,
                    title=f"物流 · {event.status}",
                    content=event.description or event.status,
                    occurred_at=event.occurred_at,
                    weight=0.8 if "签收" in event.status else 0.4,
                )
            )
            counter += 1

        for item in unboxing:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"E{counter}",
                    type=EvidenceType.UNBOXING_IMAGE,
                    title="开箱凭证",
                    content=item.description or item.image_url,
                    occurred_at=item.captured_at,
                    weight=0.75,
                )
            )
            counter += 1

        return evidence

    def _build_timeline(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
        unboxing: list[UnboxingEvidence],
    ) -> list[TimelineNode]:
        """构建时间线。

        Args:
            order: 订单。
            chat_log: 聊天记录。
            logistics: 物流轨迹。
            unboxing: 开箱凭证。

        Returns:
            按时间升序的节点列表。
        """
        nodes: list[TimelineNode] = []

        if order.paid_at:
            nodes.append(
                TimelineNode(
                    occurred_at=order.paid_at,
                    phase="下单",
                    title="完成支付",
                    detail=f"订单 {order.order_id}，金额 ¥{order.amount:.2f}",
                )
            )
        if order.shipped_at:
            nodes.append(
                TimelineNode(
                    occurred_at=order.shipped_at,
                    phase="发货",
                    title="商家发货",
                    detail=order.product_title,
                )
            )

        for event in logistics:
            phase = "运输"
            for keyword, mapped in LOGISTICS_PHASE:
                if keyword in event.status:
                    phase = mapped
                    break
            nodes.append(
                TimelineNode(
                    occurred_at=event.occurred_at,
                    phase=phase,
                    title=event.status,
                    detail=event.description or "",
                )
            )

        for message in chat_log:
            nodes.append(
                TimelineNode(
                    occurred_at=message.sent_at,
                    phase="售后",
                    title=f"{SPEAKER_LABEL.get(message.speaker, '未知')}发言",
                    detail=message.content[:120],
                )
            )

        for item in unboxing:
            nodes.append(
                TimelineNode(
                    occurred_at=item.captured_at,
                    phase="签收",
                    title="开箱凭证",
                    detail=item.description or item.image_url,
                )
            )

        nodes.sort(
            key=lambda node: node.occurred_at.timestamp()
            if node.occurred_at
            else float("inf")
        )
        return nodes

    # ------------------------------------------------------------------
    # 事实推导
    # ------------------------------------------------------------------
    @staticmethod
    def _context_text(
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
        unboxing: list[UnboxingEvidence],
        claim_text: str,
    ) -> str:
        """拼接用于关键词匹配的上下文。

        Args:
            order: 订单。
            chat_log: 聊天记录。
            logistics: 物流轨迹。
            unboxing: 开箱凭证。
            claim_text: 用户诉求。

        Returns:
            拼接文本。
        """
        parts = [claim_text, order.product_title or ""]
        parts.extend(message.content for message in chat_log)
        parts.extend(event.description or event.status for event in logistics)
        parts.extend(item.description for item in unboxing)
        return " ".join(part for part in parts if part)

    @staticmethod
    def _received_at(
        order: DisputeOrderInput, logistics: list[LogisticsEventInput]
    ) -> datetime | None:
        """确定签收时间。

        优先取订单字段，其次取物流中最晚的一条「签收」轨迹。

        Args:
            order: 订单。
            logistics: 物流轨迹。

        Returns:
            签收时间，未知时返回 None。
        """
        if order.received_at:
            return order.received_at
        stamps = [
            event.occurred_at
            for event in logistics
            if "签收" in event.status and event.occurred_at is not None
        ]
        return max(stamps) if stamps else None

    @staticmethod
    def _days_since(moment: datetime | None) -> int | None:
        """计算距今天数。

        Args:
            moment: 起算时间。

        Returns:
            天数；时间未知或时区不一致时返回 None。
        """
        if moment is None:
            return None
        try:
            delta = datetime.now(moment.tzinfo) - moment
        except TypeError:
            try:
                delta = datetime.now() - moment
            except TypeError:
                return None
        return max(0, delta.days)

    def _derive_facts(
        self,
        order: DisputeOrderInput,
        chat_log: list[ChatMessageInput],
        logistics: list[LogisticsEventInput],
        unboxing: list[UnboxingEvidence],
        context: str,
    ) -> dict[str, bool]:
        """推导规则匹配所需的事实标记。

        Args:
            order: 订单。
            chat_log: 聊天记录。
            logistics: 物流轨迹。
            unboxing: 开箱凭证。
            context: 关键词匹配上下文。

        Returns:
            事实标记字典。
        """
        facts: dict[str, bool] = {}
        for key, keywords in KEYWORD_FACTS.items():
            facts[key] = any(keyword in context for keyword in keywords)

        received_at = self._received_at(order, logistics)
        days = self._days_since(received_at)
        settings = self.settings

        facts["received"] = received_at is not None
        facts["opened"] = bool(unboxing) or any(
            keyword in context for keyword in ("拆封", "打开包装", "已拆")
        )
        facts["excluded_category"] = bool(
            order.is_custom_made or order.is_fresh or order.is_digital
        )
        facts["merchant_promised"] = any(
            keyword in " ".join(
                message.content
                for message in chat_log
                if message.speaker is Speaker.MERCHANT
            )
            for keyword in ("包退", "七天无理由", "七日无理由", "可以退")
        )

        no_reason_ok = (
            received_at is not None
            and days is not None
            and 0 <= days <= settings.dispute_seven_day_return_days
            and not facts["excluded_category"]
            and not facts["opened"]
        )
        facts["within_seven_days"] = (
            days is not None and 0 <= days <= settings.dispute_seven_day_return_days
        )
        facts["no_reason_window_ok"] = no_reason_ok
        facts["beyond_quality_window"] = (
            days is not None and days > settings.dispute_quality_return_days
        )
        facts["evidence_insufficient"] = len(unboxing) == 0 and (
            len(chat_log) < 2 or received_at is None
        )

        # 质量问题若同时有开箱影像，视为已初步举证
        if facts["quality_issue"] and unboxing:
            facts["evidence_insufficient"] = False

        return facts

    def _build_key_facts(
        self,
        facts: dict[str, bool],
        days_since_receipt: int | None,
        received_at: datetime | None,
    ) -> list[KeyFact]:
        """把事实标记转写成可读的关键事实。

        Args:
            facts: 事实标记。
            days_since_receipt: 距签收天数。
            received_at: 签收时间。

        Returns:
            关键事实列表。
        """
        items: list[KeyFact] = []

        if received_at:
            day_text = f"距今 {days_since_receipt} 天" if days_since_receipt is not None else ""
            items.append(
                KeyFact(
                    statement=f"消费者已于 {received_at:%Y-%m-%d %H:%M} 签收商品（{day_text}）",
                    evidence_ids=["E1"],
                    confidence=0.9,
                    favorable_to="neutral",
                )
            )
        else:
            items.append(
                KeyFact(
                    statement="未见明确的签收时间记录",
                    evidence_ids=["E1"],
                    confidence=0.6,
                    favorable_to="neutral",
                )
            )

        mapping: list[tuple[str, str, str]] = [
            ("quality_issue", "消费者主张商品存在质量问题", "consumer"),
            ("damage_on_arrival", "商品疑似在运输途中破损", "consumer"),
            ("description_mismatch", "实物与页面描述存在不符", "consumer"),
            ("counterfeit", "消费者质疑商品真伪", "consumer"),
            ("wrong_or_missing", "存在发错货或漏发情形", "consumer"),
            ("logistics_issue", "存在超时未发货或虚假发货情形", "consumer"),
            ("merchant_refused", "商家存在拒不处理售后情形", "consumer"),
            ("platform_ignored", "平台介入后未见处理结果", "consumer"),
            ("opened", "商品已被拆封", "merchant"),
            ("excluded_category", "商品属于七日无理由退货的除外情形", "merchant"),
            ("no_reason_window_ok", "仍处于七日无理由退货窗口内", "consumer"),
            ("beyond_quality_window", "已超出质量问题退换的常规受理窗口", "merchant"),
        ]
        for key, statement, side in mapping:
            if facts.get(key):
                items.append(
                    KeyFact(
                        statement=statement,
                        evidence_ids=["E1"],
                        confidence=0.75,
                        favorable_to=side,
                    )
                )

        return items

    def _find_gaps(
        self,
        facts: dict[str, bool],
        chat_log: list[ChatMessageInput],
        unboxing: list[UnboxingEvidence],
        received_at: datetime | None,
    ) -> list[str]:
        """识别证据缺口。

        Args:
            facts: 事实标记。
            chat_log: 聊天记录。
            unboxing: 开箱凭证。
            received_at: 签收时间。

        Returns:
            缺口描述列表。
        """
        gaps: list[str] = []

        if received_at is None:
            gaps.append("缺少签收时间，无法判断是否处于七日无理由退货窗口")

        if not unboxing and any(facts.get(key) for key in IMAGE_BACKED_FACTS):
            gaps.append("主张商品存在问题，但未提供开箱视频或照片")

        if len(chat_log) < 2:
            gaps.append("聊天记录少于 2 条，沟通过程难以完整还原")

        if facts.get("counterfeit"):
            gaps.append("主张假冒需提供品牌鉴定报告或官方验真结果")

        if facts.get("description_mismatch") and not unboxing:
            gaps.append("主张货不对板需提供与页面描述对比的实拍证据")

        if facts.get("quality_issue") and facts.get("beyond_quality_window"):
            gaps.append("已超出常规受理窗口，建议补充检测报告以强化举证")

        return gaps

    # ------------------------------------------------------------------
    # 文案
    # ------------------------------------------------------------------
    @staticmethod
    def _rule_summary(
        timeline: list[TimelineNode],
        key_facts: list[KeyFact],
        gaps: list[str],
        days_since_receipt: int | None,
    ) -> str:
        """生成规则版事实摘要。

        Args:
            timeline: 时间线。
            key_facts: 关键事实。
            gaps: 证据缺口。
            days_since_receipt: 距签收天数。

        Returns:
            摘要文本。
        """
        parts = [f"共还原 {len(timeline)} 个时间节点"]
        if days_since_receipt is not None:
            parts.append(f"签收至今 {days_since_receipt} 天")
        parts.append(f"关键事实 {len(key_facts)} 条")
        if gaps:
            parts.append(f"存在 {len(gaps)} 处证据缺口")
        else:
            parts.append("证据基本完整")
        return "，".join(parts) + "。"

    @staticmethod
    def _format_timeline(timeline: list[TimelineNode]) -> str:
        """格式化时间线用于提示词。

        Args:
            timeline: 时间线。

        Returns:
            多行文本。
        """
        lines: list[str] = []
        for node in timeline[:30]:
            stamp = f"{node.occurred_at:%Y-%m-%d %H:%M}" if node.occurred_at else "时间未知"
            lines.append(f"- {stamp} [{node.phase}] {node.title}：{node.detail}")
        return "\n".join(lines) if lines else "无"

    async def execute(self, state: DisputeState) -> AgentResult:
        """还原事实（工作流节点接口）。

        Args:
            state: 仲裁庭状态。

        Returns:
            包含事实清单的结果对象。
        """
        try:
            sheet, facts = await self.restore(
                order=state.order,
                chat_log=state.chat_log,
                logistics=state.logistics,
                unboxing=state.unboxing,
                claim_text=state.claim_text,
            )
            state.fact_sheet = sheet
            state.facts = facts
            return AgentResult(
                success=True,
                data={
                    "fact_sheet": sheet.model_dump(mode="json"),
                    "facts": facts,
                },
            )
        except Exception as exc:
            logger.exception("事实还原失败")
            return AgentResult(success=False, error=f"事实还原失败: {exc}")
