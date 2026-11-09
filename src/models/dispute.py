"""
售后纠纷仲裁庭领域模型。

Description:
    定义「售后纠纷仲裁庭」的输入与产出结构：
    - 证据材料（聊天记录 / 物流轨迹 / 开箱凭证）
    - 事实还原结果（时间线 + 关键事实 + 证据缺口）
    - 规则匹配结果（平台规则 + 法律条款 + 责任判定）
    - 话术产出（投诉 / 申诉 / 协商文本）

    说明: 模型输出仅为争议处理参考，不构成法律意见。
2026-11-09
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """证据类型。"""

    CHAT = "chat"
    LOGISTICS = "logistics"
    UNBOXING_IMAGE = "unboxing_image"
    ORDER = "order"
    INVOICE = "invoice"
    PROMISE = "promise"
    OTHER = "other"


class Speaker(str, Enum):
    """对话角色。"""

    CONSUMER = "consumer"
    MERCHANT = "merchant"
    PLATFORM = "platform"
    SYSTEM = "system"


class ChatMessageInput(BaseModel):
    """一条聊天记录。

    Attributes:
        speaker: 发言方。
        content: 内容。
        sent_at: 发送时间。
    """

    speaker: Speaker = Field(..., description="发言方")
    content: str = Field(..., min_length=1, description="消息内容")
    sent_at: datetime | None = Field(default=None, description="发送时间")


class LogisticsEventInput(BaseModel):
    """一条物流轨迹。

    Attributes:
        status: 轨迹状态，如「已揽收」「派送中」「已签收」。
        description: 轨迹描述。
        occurred_at: 发生时间。
        location: 发生地点。
    """

    status: str = Field(..., description="轨迹状态")
    description: str | None = Field(default=None, description="轨迹描述")
    occurred_at: datetime | None = Field(default=None, description="发生时间")
    location: str | None = Field(default=None, description="发生地点")


class UnboxingEvidence(BaseModel):
    """一份开箱凭证。

    Attributes:
        image_url: 图片地址。
        description: 图片说明（人工或 OCR 摘要）。
        captured_at: 拍摄时间。
    """

    image_url: str = Field(..., description="图片地址")
    description: str = Field(default="", description="图片说明")
    captured_at: datetime | None = Field(default=None, description="拍摄时间")


class DisputeOrderInput(BaseModel):
    """争议订单基础信息。

    Attributes:
        order_id: 订单号。
        platform: 平台。
        category: 商品类目。
        amount: 订单金额。
        product_title: 商品标题。
        paid_at: 支付时间。
        shipped_at: 发货时间。
        received_at: 签收时间。
        is_custom_made: 是否定制商品（七日无理由退货的除外情形）。
        is_fresh: 是否鲜活易腐（七日无理由退货的除外情形）。
        is_digital: 是否已拆封数字化商品（除外情形）。
    """

    order_id: str = Field(..., description="订单号")
    platform: str = Field(default="unknown", description="平台")
    category: str | None = Field(default=None, description="商品类目")
    amount: float = Field(default=0.0, ge=0, description="订单金额")
    product_title: str = Field(default="", description="商品标题")
    paid_at: datetime | None = Field(default=None, description="支付时间")
    shipped_at: datetime | None = Field(default=None, description="发货时间")
    received_at: datetime | None = Field(default=None, description="签收时间")
    is_custom_made: bool = Field(default=False, description="是否定制商品")
    is_fresh: bool = Field(default=False, description="是否鲜活易腐")
    is_digital: bool = Field(default=False, description="是否已拆封数字化商品")


class DisputeClaim(str, Enum):
    """用户诉求类型。"""

    REFUND_ONLY = "refund_only"
    REFUND_WITH_RETURN = "refund_with_return"
    RETURN_REPAIR = "return_repair"
    EXCHANGE = "exchange"
    COMPENSATION = "compensation"
    APOLOGY = "apology"
    UNDETERMINED = "undetermined"


class EvidenceItem(BaseModel):
    """归一化后的单条证据。

    Attributes:
        evidence_id: 证据编号。
        type: 证据类型。
        title: 证据标题。
        content: 证据正文/摘要。
        occurred_at: 发生时间。
        weight: 证明力 0-1。
    """

    evidence_id: str = Field(..., description="证据编号")
    type: EvidenceType = Field(..., description="证据类型")
    title: str = Field(..., description="证据标题")
    content: str = Field(default="", description="证据正文/摘要")
    occurred_at: datetime | None = Field(default=None, description="发生时间")
    weight: float = Field(default=0.5, ge=0, le=1, description="证明力")


class TimelineNode(BaseModel):
    """事实还原时间线上的一个节点。

    Attributes:
        occurred_at: 时间。
        phase: 阶段（下单/发货/运输/签收/售后/争议）。
        title: 节点标题。
        detail: 详情。
        source: 证据来源编号。
    """

    occurred_at: datetime | None = Field(default=None, description="时间")
    phase: str = Field(..., description="阶段")
    title: str = Field(..., description="节点标题")
    detail: str = Field(default="", description="详情")
    source: str | None = Field(default=None, description="证据来源编号")


class KeyFact(BaseModel):
    """事实还原的关键事实。

    Attributes:
        statement: 事实陈述。
        evidence_ids: 支撑证据编号。
        confidence: 置信度 0-1。
        favorable_to: 该事实倾向哪一方（consumer/merchant/neutral）。
    """

    statement: str = Field(..., description="事实陈述")
    evidence_ids: list[str] = Field(default_factory=list, description="支撑证据")
    confidence: float = Field(default=0.5, ge=0, le=1, description="置信度")
    favorable_to: str = Field(default="neutral", description="倾向方")


class FactSheet(BaseModel):
    """事实还原 Agent 的产出。

    Attributes:
        order: 争议订单。
        evidence: 归一化证据列表。
        timeline: 时间线。
        key_facts: 关键事实。
        evidence_gaps: 证据缺口。
        complete: 证据是否足以支撑判定。
        summary: 事实摘要。
    """

    order: DisputeOrderInput = Field(..., description="争议订单")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="归一化证据")
    timeline: list[TimelineNode] = Field(default_factory=list, description="时间线")
    key_facts: list[KeyFact] = Field(default_factory=list, description="关键事实")
    evidence_gaps: list[str] = Field(default_factory=list, description="证据缺口")
    complete: bool = Field(default=False, description="证据是否充分")
    summary: str = Field(default="", description="事实摘要")


class Responsibility(str, Enum):
    """责任判定。"""

    MERCHANT = "merchant"
    CONSUMER = "consumer"
    PLATFORM = "platform"
    SHARED = "shared"
    UNDETERMINED = "undetermined"


class MatchedRule(BaseModel):
    """规则解读 Agent 命中的单条规则。

    Attributes:
        rule_id: 规则编号。
        name: 规则名称。
        category: 类别（退货/质量/虚假宣传/物流/态度）。
        legal_basis: 法律条款摘要。
        conclusion: 该规则指向的结论。
        weight: 权重 0-1。
        matched_because: 命中原因。
        favors: 该规则倾向哪一方。
    """

    rule_id: str = Field(..., description="规则编号")
    name: str = Field(..., description="规则名称")
    category: str = Field(..., description="类别")
    legal_basis: str = Field(default="", description="法律条款摘要")
    conclusion: str = Field(default="", description="结论")
    weight: float = Field(default=0.5, ge=0, le=1, description="权重")
    matched_because: str = Field(default="", description="命中原因")
    favors: Responsibility = Field(
        default=Responsibility.UNDETERMINED, description="倾向方"
    )


class DraftTone(str, Enum):
    """话术语气。"""

    COMPLAINT = "complaint"
    APPEAL = "appeal"
    NEGOTIATION = "negotiation"


class ComplaintDraft(BaseModel):
    """话术生成 Agent 的产出。

    Attributes:
        tone: 语气类型。
        title: 标题。
        body: 正文。
        cited_clauses: 引用的条款。
        next_actions: 建议的后续动作。
    """

    tone: DraftTone = Field(..., description="语气类型")
    title: str = Field(..., description="标题")
    body: str = Field(..., description="正文")
    cited_clauses: list[str] = Field(default_factory=list, description="引用条款")
    next_actions: list[str] = Field(default_factory=list, description="后续动作建议")


class ArbitrationVerdict(BaseModel):
    """规则解读 Agent 的裁决。

    Attributes:
        case_id: 案件编号。
        responsibility: 责任方。
        confidence: 判定置信度。
        claim: 识别到的用户诉求。
        matched_rules: 命中规则。
        legal_basis: 引用的法律条款（去重）。
        reasoning: 判定说明。
        suggested_compensation: 建议的赔付/处理方案。
        deadline_advice: 时效提示。
    """

    case_id: str = Field(..., description="案件编号")
    responsibility: Responsibility = Field(..., description="责任方")
    confidence: float = Field(default=0.5, ge=0, le=1, description="判定置信度")
    claim: DisputeClaim = Field(default=DisputeClaim.UNDETERMINED, description="用户诉求")
    matched_rules: list[MatchedRule] = Field(default_factory=list, description="命中规则")
    legal_basis: list[str] = Field(default_factory=list, description="引用条款")
    reasoning: str = Field(default="", description="判定说明")
    suggested_compensation: str = Field(default="", description="建议处理方案")
    deadline_advice: str = Field(default="", description="时效提示")


class DisputeCaseResult(BaseModel):
    """仲裁庭完整产出。

    Attributes:
        case_id: 案件编号。
        order_id: 订单号。
        verdict: 裁决。
        fact_sheet: 事实还原结果。
        drafts: 话术草稿。
        disclaimer: 免责声明。
        generated_at: 生成时间。
    """

    case_id: str = Field(..., description="案件编号")
    order_id: str = Field(..., description="订单号")
    verdict: ArbitrationVerdict = Field(..., description="裁决")
    fact_sheet: FactSheet = Field(..., description="事实还原结果")
    drafts: list[ComplaintDraft] = Field(default_factory=list, description="话术草稿")
    disclaimer: str = Field(default="", description="免责声明")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")
