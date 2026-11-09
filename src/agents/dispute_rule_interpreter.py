"""
规则解读 Agent。

Description:
    把事实还原结果送进规则库匹配，聚合出责任方与置信度，
    再给出可执行的赔付/处理建议与时效提示。

    判定逻辑是「加权投票 + 相近则共担」：每条规则按权重投给一方，
    双方权重差距小于 20% 时判为共担，避免一两句话就一边倒。
2026-11-09
"""

import logging
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentResult, AgentRole
from src.agents.consumer_base import ConsumerAgentBase
from src.agents.dispute_rules import aggregate_responsibility, match_rules
from src.graph.dispute_state import DisputeState
from src.models.dispute import (
    ArbitrationVerdict,
    DisputeClaim,
    FactSheet,
    Responsibility,
)

logger = logging.getLogger(__name__)

# 诉求识别的关键词（按优先级排列，先命中先返回）
CLAIM_PATTERNS: tuple[tuple[DisputeClaim, tuple[str, ...]], ...] = (
    (DisputeClaim.COMPENSATION, ("赔偿", "三倍", "索赔", "赔我")),
    (DisputeClaim.EXCHANGE, ("换货", "换新", "换个", "换一个")),
    (DisputeClaim.RETURN_REPAIR, ("维修", "修理", "补发")),
    (DisputeClaim.REFUND_WITH_RETURN, ("退货退款", "退货", "退货退款")),
    (DisputeClaim.REFUND_ONLY, ("仅退款", "只退款", "退钱", "退款")),
    (DisputeClaim.APOLOGY, ("道歉", "赔礼")),
)


def _split_clauses(text: str) -> list[str]:
    """把条款串拆成单条条款，便于跨规则去重。

    不同规则可能共用同一部法律（例如都引用《消费者权益保护法》第二十四条），
    直接按整串去重会把重复条款保留下来，按句拆分后再去重才能真正去重。

    Args:
        text: 条款串。

    Returns:
        单条条款列表。
    """
    if not text:
        return []
    return [part.strip() for part in re.split(r"(?<=。)", text) if part.strip()]


class RuleInterpreterAgent(ConsumerAgentBase[DisputeState]):
    """规则解读 Agent。

    Example:
        >>> interpreter = RuleInterpreterAgent(enable_llm=False)
        >>> verdict = await interpreter.interpret("case_1", sheet, facts, "要求退货退款")
        >>> verdict.responsibility.value in {"merchant", "consumer", "shared", "undetermined"}
        True
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化规则解读 Agent。

        Args:
            enable_llm: 是否允许 LLM 生成判定说明。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.DISPUTE_RULE_INTERPRETER,
            enable_llm=enable_llm,
            **kwargs,
        )
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """注册提示模板。"""
        self.register_prompt(
            "reasoning",
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是一名熟悉电商平台争议规则的调解员。根据命中规则与责任判定，"
                        "用不超过 120 字的中文说明判定理由：先讲事实，再讲依据，最后给结论。"
                        "只能引用输入中出现的条款，不得虚构法条或金额。",
                    ),
                    (
                        "human",
                        "事实要点：\n{facts}\n\n命中规则：\n{rules}\n\n"
                        "责任判定：{responsibility}\n规则版理由：{reasoning}",
                    ),
                ]
            ),
        )

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    async def interpret(
        self,
        case_id: str,
        fact_sheet: FactSheet,
        facts: dict[str, bool],
        claim_text: str = "",
    ) -> ArbitrationVerdict:
        """解读规则并给出裁决。

        Args:
            case_id: 案件编号。
            fact_sheet: 事实还原结果。
            facts: 事实标记。
            claim_text: 用户诉求原文。

        Returns:
            裁决结果。
        """
        context = self._context_text(fact_sheet, claim_text)
        matched = match_rules(facts, context)
        responsibility, confidence = aggregate_responsibility(matched)
        claim = self._detect_claim(claim_text, responsibility)

        legal_basis: list[str] = []
        for rule in matched:
            for clause in _split_clauses(rule.legal_basis):
                if clause not in legal_basis:
                    legal_basis.append(clause)

        reasoning = self._rule_reasoning(fact_sheet, matched, responsibility)
        polished = await self.try_generate(
            self.get_prompt("reasoning"),
            {
                "facts": "\n".join(f"- {item.statement}" for item in fact_sheet.key_facts) or "无",
                "rules": "\n".join(
                    f"- {rule.name}：{rule.conclusion}" for rule in matched
                )
                or "无命中规则",
                "responsibility": responsibility.value,
                "reasoning": reasoning,
            },
            accept=lambda text: 15 <= len(text) <= 300,
        )
        if polished:
            reasoning = polished

        return ArbitrationVerdict(
            case_id=case_id,
            responsibility=responsibility,
            confidence=confidence,
            claim=claim,
            matched_rules=matched,
            legal_basis=legal_basis,
            reasoning=reasoning,
            suggested_compensation=self._suggest_compensation(facts, responsibility, claim),
            deadline_advice=self._deadline_advice(facts),
        )

    @staticmethod
    def _context_text(fact_sheet: FactSheet, claim_text: str) -> str:
        """拼接规则匹配用的上下文。

        Args:
            fact_sheet: 事实清单。
            claim_text: 用户诉求。

        Returns:
            拼接文本。
        """
        parts = [claim_text, fact_sheet.order.product_title or ""]
        parts.extend(item.content for item in fact_sheet.evidence)
        return " ".join(part for part in parts if part)

    @staticmethod
    def _detect_claim(text: str, responsibility: Responsibility) -> DisputeClaim:
        """识别用户诉求类型。

        Args:
            text: 诉求原文。
            responsibility: 责任判定（用于缺省推断）。

        Returns:
            诉求类型。
        """
        for claim, keywords in CLAIM_PATTERNS:
            if any(keyword in text for keyword in keywords):
                return claim
        if responsibility is Responsibility.MERCHANT:
            return DisputeClaim.REFUND_WITH_RETURN
        return DisputeClaim.UNDETERMINED

    # ------------------------------------------------------------------
    # 文案
    # ------------------------------------------------------------------
    @staticmethod
    def _rule_reasoning(
        fact_sheet: FactSheet,
        matched: list[Any],
        responsibility: Responsibility,
    ) -> str:
        """生成规则版判定理由。

        Args:
            fact_sheet: 事实清单。
            matched: 命中规则。
            responsibility: 责任判定。

        Returns:
            判定说明。
        """
        if not matched:
            return (
                "现有证据未能匹配到具体争议规则，判定为责任不明。"
                "建议补充开箱视频、质检报告或与商家的书面沟通记录后再次申请。"
            )

        top_rules = "；".join(f"「{rule.name}」" for rule in matched[:3])
        facts_text = (
            fact_sheet.key_facts[0].statement if fact_sheet.key_facts else "事实尚不完整"
        )
        label = {
            Responsibility.MERCHANT: "商家应承担责任",
            Responsibility.CONSUMER: "消费者诉求依据不足",
            Responsibility.PLATFORM: "平台需承担相应责任",
            Responsibility.SHARED: "双方按比例共担责任",
            Responsibility.UNDETERMINED: "责任暂无法认定",
        }[responsibility]
        return f"{facts_text}。依据{top_rules}等规则综合判断：{label}。"

    @staticmethod
    def _suggest_compensation(
        facts: dict[str, bool],
        responsibility: Responsibility,
        claim: DisputeClaim,
    ) -> str:
        """给出处理方案建议。

        Args:
            facts: 事实标记。
            responsibility: 责任判定。
            claim: 诉求类型。

        Returns:
            方案文本。
        """
        if responsibility is Responsibility.PLATFORM:
            return "可要求平台介入处理；平台明知商家侵权仍未处理的，可主张连带责任。"

        if responsibility is Responsibility.SHARED:
            return "双方均有责任，建议协商部分退款（常见区间为 30%-50%）。"

        if responsibility is Responsibility.UNDETERMINED:
            return "证据不足以支撑单方责任，建议先补充证据再申请平台介入。"

        if responsibility is Responsibility.CONSUMER:
            if facts.get("opened"):
                return (
                    "商品已拆封且无质量问题证据，商家可主张影响二次销售；"
                    "建议协商部分退款或折价补偿。"
                )
            if facts.get("excluded_category"):
                return "商品属于七日无理由例外情形，建议以协商方式解决，不宜强行主张无理由退货。"
            return "现有证据不足以证明商家违约，建议补充证据后再主张权利。"

        # 责任在商家
        if facts.get("counterfeit"):
            return "可要求退还货款，并主张三倍价款赔偿（增加赔偿金额不足 500 元的按 500 元计）。"
        if facts.get("description_mismatch"):
            return "可要求退货退款；若构成欺诈，可另行主张三倍赔偿。"
        if facts.get("damage_on_arrival"):
            return "可要求补发、换货或全额退款，往返运费由商家承担。"
        if facts.get("wrong_or_missing"):
            return "可要求补发或换货；无法补发的应全额退款。"
        if facts.get("logistics_issue"):
            return "可申请全额退款，并按平台规则主张延迟发货违约金。"
        if facts.get("quality_issue"):
            return "可要求退货退款或换货，并保留检测费用索赔的权利。"
        return "可要求退货退款，并由商家承担退货运费。"

    def _deadline_advice(self, facts: dict[str, bool]) -> str:
        """生成时效提示。

        Args:
            facts: 事实标记。

        Returns:
            时效建议。
        """
        window = self.settings.dispute_seven_day_return_days
        if not facts.get("received"):
            return "尚未确认签收时间，建议先核对物流签收记录，避免错过受理时限。"
        if facts.get("no_reason_window_ok"):
            return f"仍处于七日无理由退货窗口内（{window} 天），建议尽快提交申请并保持商品完好。"
        if facts.get("within_seven_days"):
            return (
                f"签收未满 {window} 天，但商品已拆封或属法定除外情形，"
                "无理由退货可能被主张影响二次销售；若存在质量问题，"
                "可依据《消费者权益保护法》第二十四条主张退货或换货。"
            )
        if facts.get("beyond_quality_window"):
            return (
                "已超出质量问题退换的常规受理窗口，"
                "需以质量检测报告等证据主张权利，必要时可向平台投诉。"
            )
        return (
            "已超出七日无理由窗口，但若有质量问题证据，"
            "仍可依据《消费者权益保护法》第二十四条主张退货或换货。"
        )

    async def execute(self, state: DisputeState) -> AgentResult:
        """解读规则（工作流节点接口）。

        Args:
            state: 仲裁庭状态。

        Returns:
            包含裁决的结果对象。
        """
        try:
            if state.fact_sheet is None:
                return AgentResult(success=False, error="缺少事实还原结果，无法进行规则匹配")

            verdict = await self.interpret(
                case_id=state.case_id,
                fact_sheet=state.fact_sheet,
                facts=state.facts,
                claim_text=state.claim_text,
            )
            state.verdict = verdict
            return AgentResult(
                success=True,
                data={"verdict": verdict.model_dump(mode="json")},
            )
        except Exception as exc:
            logger.exception("规则解读失败")
            return AgentResult(success=False, error=f"规则解读失败: {exc}")
