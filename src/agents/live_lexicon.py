"""
直播口播词库与弹幕情感词典。

Description:
    为「直播购物分身」提供规则底座：
    - 口播关键词：识别价格、限量、赠品、时效、规格、承诺
    - 弹幕情感词典：判断单条弹幕的正负向，统计高频短语

    直播场景的特点是「说得快、重复多、口语化」，因此这里优先用短语级匹配
    而不是依赖模型，保证在弱网/无模型环境下也能实时出结果。
2026-11-09
"""

import re

from src.models.live import KeyPointKind

# 价格抽取正则，按优先级尝试
PRICE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:¥|￥)\s*(\d+(?:\.\d+)?)"),
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:元|块钱|块)"),
    re.compile(r"(?:价格|售价|到手价|福利价|秒杀价|直播间价)\s*[:：]?\s*(\d+(?:\.\d+)?)"),
)

# 各类关键信息的关键词
KEY_POINT_KEYWORDS: dict[KeyPointKind, tuple[str, ...]] = {
    KeyPointKind.LIMIT: ("限量", "限购", "仅剩", "库存", "只发", "抢完", "仅限", "最后"),
    KeyPointKind.GIFT: ("赠", "送", "加赠", "拍一发", "买一送", "赠品", "送完为止", "附赠"),
    KeyPointKind.DEADLINE: ("限时", "今天", "今晚", "截止", "倒计时", "小时内", "前100名", "分钟后"),
    KeyPointKind.PROMISE: (
        "假一赔",
        "七天无理由",
        "七日无理由",
        "包邮",
        "退换",
        "保修",
        "正品",
        "顺丰",
        "运费险",
    ),
}

# 一句话里同时命中多类信息时的取舍顺序：
# 价格最硬、赠品与限量次之，规格只是陪衬，因此一句只保留一个主类型，
# 避免「限量500件」被同时记成限量/时效/规格三条噪音。
KIND_PRIORITY: tuple[KeyPointKind, ...] = (
    KeyPointKind.PRICE,
    KeyPointKind.GIFT,
    KeyPointKind.LIMIT,
    KeyPointKind.DEADLINE,
    KeyPointKind.PROMISE,
    KeyPointKind.SPEC,
)

# 规格单位
SPEC_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*(?:ml|g|kg|L|cm|mm|寸|码|件|支|片|包|瓶|盒|抽|只)")

# 弹幕情感词（正向）
POSITIVE_PHRASES: tuple[str, ...] = (
    "冲",
    "划算",
    "真香",
    "入手",
    "便宜",
    "好看",
    "值",
    "买它",
    "已拍",
    "下单",
    "抢到",
    "满意",
    "支持",
    "爱了",
    "牛",
    "香",
    "实惠",
    "种草",
)

# 弹幕情感词（负向）
NEGATIVE_PHRASES: tuple[str, ...] = (
    "太贵",
    "贵了",
    "智商税",
    "割韭菜",
    "劝退",
    "坑",
    "不值",
    "别买",
    "翻车",
    "拉胯",
    "一般",
    "失望",
    "退",
    "假",
    "犹豫",
    "套路",
    "划不来",
)

# 情感判定的否定前缀：出现时反转情感极性
NEGATION_PREFIXES: tuple[str, ...] = ("不", "没", "别")

SENTENCE_SPLIT = re.compile(r"[，,。！!？?；;\n]+")


def split_sentences(text: str) -> list[str]:
    """按中英文标点把口播文本切成短句。

    Args:
        text: 口播文本。

    Returns:
        短句列表。
    """
    return [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]


def extract_prices(text: str) -> list[float]:
    """抽取文本中的价格数字。

    Args:
        text: 待抽取文本。

    Returns:
        价格列表，按出现顺序。
    """
    prices: list[float] = []
    for pattern in PRICE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                value = float(match.group(1))
            except (TypeError, ValueError):
                continue
            if value <= 0:
                continue
            if value not in prices:
                prices.append(value)
    return prices


def detect_kinds(sentence: str) -> list[KeyPointKind]:
    """判断一个短句的主类型。

    一句口播常常同时携带多种信息（「限量500件」既像限量又像规格），
    这里按 ``KIND_PRIORITY`` 只保留优先级最高的一个，避免同一句话被拆成多条噪音。

    Args:
        sentence: 短句。

    Returns:
        命中的信息类型列表（0 或 1 个元素）。
    """
    present: set[KeyPointKind] = set()
    if extract_prices(sentence):
        present.add(KeyPointKind.PRICE)
    for kind, keywords in KEY_POINT_KEYWORDS.items():
        if any(keyword in sentence for keyword in keywords):
            present.add(kind)
    if SPEC_PATTERN.search(sentence):
        present.add(KeyPointKind.SPEC)

    for kind in KIND_PRIORITY:
        if kind in present:
            return [kind]
    return []


def classify_danmaku(text: str) -> str:
    """判断单条弹幕的情感极性。

    Args:
        text: 弹幕文本。

    Returns:
        ``positive`` / ``negative`` / ``neutral``。
    """
    negative_hit = [phrase for phrase in NEGATIVE_PHRASES if phrase in text]
    positive_hit = [phrase for phrase in POSITIVE_PHRASES if phrase in text]

    # 「不贵」「没套路」这类否定表达需要反转极性
    if negative_hit and any(
        f"{prefix}{phrase}" in text for prefix in NEGATION_PREFIXES for phrase in negative_hit
    ):
        negative_hit = []

    if negative_hit and not positive_hit:
        return "negative"
    if positive_hit and not negative_hit:
        return "positive"
    if negative_hit and positive_hit:
        # 同时出现时，负向词通常更具体（如「贵」「坑」），优先判负
        return "negative"
    return "neutral"


def matched_phrases(text: str, phrases: tuple[str, ...]) -> list[str]:
    """返回文本中命中的短语。

    Args:
        text: 文本。
        phrases: 短语表。

    Returns:
        命中的短语列表。
    """
    return [phrase for phrase in phrases if phrase in text]
