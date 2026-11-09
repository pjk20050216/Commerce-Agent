"""
平台争议规则库。

Description:
    为「规则解读 Agent」提供可审计的规则底座。每条规则包含：
    - 触发条件（基于事实标记的声明式条件，便于单测覆盖）
    - 法律依据（条款摘要）
    - 倾向方（该规则支持谁）

    条款文本为要点摘录，正式引用请以官方发布文本为准；
    本模块只做争议处理参考，不构成法律意见。
2026-11-09
"""

from dataclasses import dataclass, field

from src.models.dispute import MatchedRule, Responsibility


@dataclass(frozen=True)
class DisputeRule:
    """单条争议规则。

    Attributes:
        rule_id: 规则编号。
        name: 规则名称。
        category: 类别。
        legal_basis: 法律条款摘要。
        conclusion: 该规则指向的结论。
        favors: 规则倾向方（CONSUMER 表示支持消费者诉求，责任在商家）。
        weight: 权重 0-1。
        conditions: 必须同时满足的事实条件。
        keywords: 命中任一关键词即可激活（与 conditions 为「且」关系）。
    """

    rule_id: str
    name: str
    category: str
    legal_basis: str
    conclusion: str
    favors: Responsibility
    weight: float
    conditions: dict[str, bool] = field(default_factory=dict)
    keywords: tuple[str, ...] = ()


# 法律条款摘要常量，避免同一句话在多处重复
LAW_RETURN_QUALITY = (
    "《消费者权益保护法》第二十四条：经营者提供的商品或者服务不符合质量要求的，"
    "消费者可以依照国家规定、当事人约定退货，或者要求经营者履行更换、修理等义务。"
)
LAW_SEVEN_DAY = (
    "《消费者权益保护法》第二十五条：经营者采用网络等方式销售商品，"
    "消费者有权自收到商品之日起七日内退货，且无需说明理由（定制、鲜活易腐、"
    "已拆封数字化商品等除外）。"
)
LAW_SEVEN_DAY_INTACT = (
    "《网络购买商品七日无理由退货暂行办法》第七条：消费者退回的商品应当完好。"
)
LAW_FRAUD = (
    "《消费者权益保护法》第五十五条：经营者提供商品或者服务有欺诈行为的，"
    "应当按照消费者的要求增加赔偿其受到的损失，增加赔偿的金额为价款的三倍；"
    "增加赔偿的金额不足五百元的，为五百元。"
)
LAW_FALSE_AD = (
    "《广告法》第二十八条：广告以虚假或者引人误解的内容欺骗、误导消费者的，"
    "构成虚假广告。"
)
LAW_CONTRACT = (
    "《民法典》第五百七十七条：当事人一方不履行合同义务或者履行合同义务不符合约定的，"
    "应当承担继续履行、采取补救措施或者赔偿损失等违约责任。"
)
LAW_DELIVERY_RISK = (
    "《民法典》第六百零四条：标的物毁损、灭失的风险，在标的物交付之前由出卖人承担，"
    "交付之后由买受人承担。"
)
LAW_DIGNITY = (
    "《消费者权益保护法》第十四条：消费者享有人格尊严、民族风俗习惯得到尊重的权利。"
)
LAW_PLATFORM_DUTY = (
    "《电子商务法》第三十八条：电子商务平台经营者知道或者应当知道平台内经营者"
    "侵害消费者合法权益，未采取必要措施的，依法与该经营者承担连带责任。"
)
LAW_DELIVERY_PROMISE = (
    "《电子商务法》第二十条：电子商务经营者应当按照承诺或者与消费者约定的方式、"
    "时限向消费者交付商品。"
)

# 平台通用争议处理规则（各家细则不同，这里抽取共性部分）
DISPUTE_RULES: tuple[DisputeRule, ...] = (
    DisputeRule(
        rule_id="R-QUALITY-01",
        name="质量问题退换货（窗口期内）",
        category="质量",
        legal_basis=LAW_RETURN_QUALITY,
        conclusion="商品存在质量问题且在受理窗口内，消费者有权要求退货退款或换货。",
        favors=Responsibility.CONSUMER,
        weight=0.9,
        conditions={"quality_issue": True, "beyond_quality_window": False},
        keywords=("质量问题", "坏了", "破损", "瑕疵", "无法使用", "不工作", "漏"),
    ),
    DisputeRule(
        rule_id="R-QUALITY-02",
        name="质量问题（超出窗口期）",
        category="质量",
        legal_basis=LAW_RETURN_QUALITY,
        conclusion="超出约定窗口但仍在合理期限内，需由消费者举证质量问题成立。",
        favors=Responsibility.CONSUMER,
        weight=0.6,
        conditions={"quality_issue": True, "beyond_quality_window": True},
    ),
    DisputeRule(
        rule_id="R-NOREASON-01",
        name="七日无理由退货",
        category="退货",
        legal_basis=LAW_SEVEN_DAY,
        conclusion="商品不属于法定除外情形且未影响二次销售的，消费者可在七日内无理由退货。",
        favors=Responsibility.CONSUMER,
        weight=0.85,
        conditions={"no_reason_window_ok": True},
        keywords=("七天无理由", "七日无理由", "无理由退货", "不想要了", "不喜欢"),
    ),
    DisputeRule(
        rule_id="R-NOREASON-02",
        name="七日无理由的除外情形",
        category="退货",
        legal_basis=LAW_SEVEN_DAY,
        conclusion="定制、鲜活易腐、已拆封数字化商品等不适用七日无理由退货。",
        favors=Responsibility.MERCHANT,
        weight=0.8,
        conditions={"excluded_category": True},
    ),
    DisputeRule(
        rule_id="R-NOREASON-03",
        name="商品已拆封影响二次销售",
        category="退货",
        legal_basis=LAW_SEVEN_DAY_INTACT,
        conclusion="商品已拆封且非质量问题，商家可主张影响二次销售而拒绝无理由退货。",
        favors=Responsibility.MERCHANT,
        weight=0.6,
        conditions={"opened": True, "quality_issue": False},
    ),
    DisputeRule(
        rule_id="R-FRAUD-01",
        name="虚假宣传 / 货不对板",
        category="虚假宣传",
        legal_basis=LAW_FRAUD + LAW_FALSE_AD,
        conclusion="实物与页面描述存在实质性不符的，可主张退货退款并追究欺诈责任。",
        favors=Responsibility.CONSUMER,
        weight=0.95,
        conditions={"description_mismatch": True},
        keywords=("与描述不符", "货不对板", "实物不符", "虚假宣传", "和图片不一样"),
    ),
    DisputeRule(
        rule_id="R-FRAUD-02",
        name="假冒品牌",
        category="虚假宣传",
        legal_basis=LAW_FRAUD,
        conclusion="经鉴定为假冒商品的，消费者可主张退还货款并要求三倍价款赔偿。",
        favors=Responsibility.CONSUMER,
        weight=1.0,
        conditions={"counterfeit": True},
        keywords=("假货", "假冒", "仿品", "不是正品", "高仿"),
    ),
    DisputeRule(
        rule_id="R-DAMAGE-01",
        name="运输途中破损",
        category="物流",
        legal_basis=LAW_DELIVERY_RISK + LAW_RETURN_QUALITY,
        conclusion="交付前发生的破损由商家承担，消费者可要求补发、换货或全额退款。",
        favors=Responsibility.CONSUMER,
        weight=0.9,
        conditions={"damage_on_arrival": True},
        keywords=("压坏", "破损", "碎了", "摔坏", "包装破损"),
    ),
    DisputeRule(
        rule_id="R-WRONG-01",
        name="发错货 / 漏发",
        category="履约",
        legal_basis=LAW_CONTRACT,
        conclusion="商家未按约定交付商品的，应补发、换货或退款并承担相应运费。",
        favors=Responsibility.CONSUMER,
        weight=0.9,
        conditions={"wrong_or_missing": True},
        keywords=("发错", "漏发", "少件", "错货", "少发"),
    ),
    DisputeRule(
        rule_id="R-LOGISTICS-01",
        name="超时未发货 / 虚假发货",
        category="物流",
        legal_basis=LAW_DELIVERY_PROMISE,
        conclusion="商家未按承诺时限交付的，消费者可要求退款并按平台规则主张违约金。",
        favors=Responsibility.CONSUMER,
        weight=0.7,
        conditions={"logistics_issue": True},
        keywords=("虚假发货", "物流不动", "一直不发货", "超时未发"),
    ),
    DisputeRule(
        rule_id="R-REFUND-01",
        name="商家拒不履行退款义务",
        category="售后",
        legal_basis=LAW_RETURN_QUALITY + LAW_CONTRACT,
        conclusion="符合退货条件的，商家拒绝退款构成违约，可申请平台介入或投诉。",
        favors=Responsibility.CONSUMER,
        weight=0.75,
        conditions={"merchant_refused": True},
        keywords=("拒绝退款", "不给退", "拒绝退换", "客服不理", "拖着不退"),
    ),
    DisputeRule(
        rule_id="R-ATTITUDE-01",
        name="服务态度与人格尊严",
        category="服务",
        legal_basis=LAW_DIGNITY,
        conclusion="商家存在辱骂、威胁等行为的，可向平台投诉并要求处理。",
        favors=Responsibility.CONSUMER,
        weight=0.4,
        conditions={},
        keywords=("辱骂", "态度恶劣", "威胁", "人身攻击"),
    ),
    DisputeRule(
        rule_id="R-PLATFORM-01",
        name="平台未履行必要措施",
        category="平台责任",
        legal_basis=LAW_PLATFORM_DUTY,
        conclusion="平台明知商家侵权仍未处理的，可主张平台承担连带责任。",
        favors=Responsibility.PLATFORM,
        weight=0.8,
        conditions={"platform_ignored": True},
        keywords=("平台不管", "投诉无果", "平台不作为", "平台推卸"),
    ),
    DisputeRule(
        rule_id="R-EVIDENCE-01",
        name="证据不足",
        category="举证",
        legal_basis="争议处理一般规则：主张方对其主张的事实承担举证责任。",
        conclusion="现有证据不足以证明质量或履约问题，建议补充开箱视频、检测报告等。",
        favors=Responsibility.UNDETERMINED,
        weight=0.5,
        conditions={"evidence_insufficient": True},
    ),
)

# 关键词 → 事实标记的映射，供事实还原阶段使用
KEYWORD_FACTS: dict[str, tuple[str, ...]] = {
    "quality_issue": (
        "质量问题",
        "坏了",
        "瑕疵",
        "无法使用",
        "不工作",
        "脱落",
        "开线",
        "掉色",
        "故障",
        "损坏",
        "有问题",
        "不能用",
        "漏",
    ),
    "damage_on_arrival": ("压坏", "破损", "碎了", "摔坏", "包装破损", "变形"),
    "description_mismatch": (
        "与描述不符",
        "货不对板",
        "实物不符",
        "虚假宣传",
        "和图片不一样",
        "色差",
        "不是同一款",
    ),
    "counterfeit": ("假货", "假冒", "仿品", "不是正品", "高仿"),
    "wrong_or_missing": ("发错", "漏发", "少件", "错货", "少发", "缺件"),
    "logistics_issue": ("虚假发货", "物流不动", "一直不发货", "超时未发", "物流停"),
    "merchant_refused": (
        "拒绝退款",
        "不给退",
        "拒绝退换",
        "客服不理",
        "拖着不退",
        "拒不处理",
    ),
    "platform_ignored": ("平台不管", "投诉无果", "平台不作为", "平台推卸"),
}


def _conditions_met(rule: DisputeRule, facts: dict[str, bool]) -> bool:
    """检查规则的事实条件是否全部满足。

    Args:
        rule: 规则。
        facts: 事实标记字典。

    Returns:
        是否满足。
    """
    return all(facts.get(key) is expected for key, expected in rule.conditions.items())


def _keywords_hit(rule: DisputeRule, context_text: str) -> bool:
    """检查规则关键词是否命中上下文。

    Args:
        rule: 规则。
        context_text: 拼接后的上下文文本。

    Returns:
        是否命中。
    """
    if not rule.keywords:
        return True
    return any(keyword in context_text for keyword in rule.keywords)


def match_rules(facts: dict[str, bool], context_text: str) -> list[MatchedRule]:
    """匹配适用于当前争议的规则。

    匹配策略分两类，避免「事实已确认却因措辞不同匹配不上」：

    - 声明了事实条件的规则：由事实决定，关键词不参与拦截；
    - 未声明事实条件的规则：由关键词触发（例如辱骂、态度类）。

    Args:
        facts: 事实标记字典。
        context_text: 用户诉求 + 聊天记录 + 证据描述的拼接文本。

    Returns:
        命中的规则列表，按权重降序。
    """
    matched: list[MatchedRule] = []
    for rule in DISPUTE_RULES:
        if rule.conditions:
            if not _conditions_met(rule, facts):
                continue
            reason = "基于已确认事实自动命中"
        else:
            if not _keywords_hit(rule, context_text):
                continue
            hit_keywords = [keyword for keyword in rule.keywords if keyword in context_text]
            reason = f"命中表述「{'、'.join(hit_keywords[:3])}」"

        matched.append(
            MatchedRule(
                rule_id=rule.rule_id,
                name=rule.name,
                category=rule.category,
                legal_basis=rule.legal_basis,
                conclusion=rule.conclusion,
                weight=rule.weight,
                matched_because=reason,
                favors=rule.favors,
            )
        )
    return sorted(matched, key=lambda item: item.weight, reverse=True)


def aggregate_responsibility(
    matched: list[MatchedRule],
) -> tuple[Responsibility, float]:
    """根据命中规则聚合责任判定。

    Args:
        matched: 命中规则列表。

    Returns:
        ``(责任方, 置信度)`` 二元组。

    规则倾向消费者 → 责任判给商家；倾向商家 → 判给消费者；
    倾向平台 → 判给平台；双方权重接近时判为共担。
    """
    if not matched:
        return Responsibility.UNDETERMINED, 0.3

    buckets: dict[Responsibility, float] = {}
    for rule in matched:
        buckets[rule.favors] = buckets.get(rule.favors, 0.0) + rule.weight

    total = sum(buckets.values())
    if total <= 0:
        return Responsibility.UNDETERMINED, 0.3

    top_party, top_weight = max(buckets.items(), key=lambda item: item[1])
    confidence = round(min(1.0, top_weight / total), 2)

    merchant_side = buckets.get(Responsibility.CONSUMER, 0.0)  # 规则支持消费者 → 商家担责
    consumer_side = buckets.get(Responsibility.MERCHANT, 0.0)

    # 双方权重接近（差距 < 20%）时判为共担，避免一边倒误判
    if merchant_side > 0 and consumer_side > 0:
        gap = abs(merchant_side - consumer_side) / max(merchant_side, consumer_side)
        if gap < 0.2:
            return Responsibility.SHARED, round(confidence * 0.8, 2)

    if top_party is Responsibility.CONSUMER:
        return Responsibility.MERCHANT, confidence
    if top_party is Responsibility.MERCHANT:
        return Responsibility.CONSUMER, confidence
    if top_party is Responsibility.PLATFORM:
        return Responsibility.PLATFORM, confidence
    return Responsibility.UNDETERMINED, round(confidence * 0.6, 2)
