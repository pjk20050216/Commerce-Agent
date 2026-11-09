"""
差评关键词词库与退货率基准。

Description:
    为「质检员 Agent」提供可解释的规则底座：把中文差评里反复出现的缺陷词
    归到固定类别并赋予严重度，再用类目退货率基准做横向对比。

    相比直接让 LLM 自由发挥，词库的好处是可复现、可审计：
    用户能看到「掉色」出现了多少次、命中了哪几条原评。
2026-11-09
"""

import re

from src.models.buyer import DefectKeyword

# 缺陷关键词 → (缺陷类别, 基础严重度 0-1)
DEFECT_LEXICON: dict[str, tuple[str, float]] = {
    # ---------- 做工 ----------
    "开线": ("做工", 0.7),
    "脱线": ("做工", 0.7),
    "线头": ("做工", 0.3),
    "破洞": ("做工", 0.8),
    "走线歪": ("做工", 0.5),
    "拉链坏": ("做工", 0.7),
    "扣子掉": ("做工", 0.6),
    "做工差": ("做工", 0.7),
    "做工粗糙": ("做工", 0.7),
    # ---------- 材质 / 色牢度 ----------
    "掉色": ("材质", 0.8),
    "褪色": ("材质", 0.8),
    "起球": ("材质", 0.6),
    "缩水": ("材质", 0.7),
    "掉毛": ("材质", 0.6),
    "掉钻": ("材质", 0.7),
    "掉漆": ("材质", 0.6),
    "异味": ("材质", 0.7),
    "刺鼻": ("材质", 0.8),
    "甲醛": ("材质", 1.0),
    "偏薄": ("材质", 0.5),
    "太薄": ("材质", 0.5),
    "透光": ("材质", 0.5),
    "偏硬": ("材质", 0.4),
    "起皱": ("材质", 0.4),
    "变形": ("材质", 0.7),
    # ---------- 尺码 ----------
    "偏小": ("尺码", 0.5),
    "偏大": ("尺码", 0.5),
    "尺码不准": ("尺码", 0.6),
    "尺码偏小": ("尺码", 0.6),
    "尺码偏大": ("尺码", 0.6),
    "穿不下": ("尺码", 0.6),
    "不合身": ("尺码", 0.5),
    # ---------- 色差 ----------
    "色差": ("色差", 0.6),
    "颜色不对": ("色差", 0.7),
    "实物不符": ("色差", 0.8),
    "和图片不一样": ("色差", 0.8),
    # ---------- 功能 ----------
    "漏水": ("功能", 0.9),
    "漏电": ("功能", 1.0),
    "不制冷": ("功能", 0.9),
    "噪音大": ("功能", 0.5),
    "卡顿": ("功能", 0.6),
    "死机": ("功能", 0.8),
    "续航差": ("功能", 0.6),
    "充电慢": ("功能", 0.4),
    "不工作": ("功能", 0.9),
    "没反应": ("功能", 0.8),
    "断裂": ("功能", 0.9),
    "不耐用": ("功能", 0.7),
    # ---------- 描述不符 / 真伪 ----------
    "货不对板": ("描述不符", 1.0),
    "与描述不符": ("描述不符", 0.9),
    "假货": ("描述不符", 1.0),
    "翻新": ("描述不符", 0.9),
    "少件": ("描述不符", 0.7),
    "漏发": ("描述不符", 0.7),
    "发错": ("描述不符", 0.6),
    # ---------- 物流 / 包装 ----------
    "发货慢": ("物流", 0.4),
    "物流慢": ("物流", 0.4),
    "虚假发货": ("物流", 0.9),
    "包装破损": ("物流", 0.6),
    "压坏": ("物流", 0.7),
    "物流丢件": ("物流", 0.9),
    # ---------- 服务 ----------
    "客服不理": ("服务", 0.8),
    "客服态度": ("服务", 0.6),
    "不退款": ("服务", 0.9),
    "拒绝退换": ("服务", 0.9),
    "态度恶劣": ("服务", 0.8),
}

# 判定一条评价是否为差评的语气标记
NEGATIVE_MARKERS: tuple[str, ...] = (
    "差",
    "烂",
    "垃圾",
    "不值",
    "后悔",
    "踩雷",
    "翻车",
    "退货",
    "退了",
    "瑕疵",
    "难用",
    "不满意",
    "失望",
    "骗人",
    "坑",
    "避雷",
    "别买",
    "智商税",
)

# 类目退货率基准（行业经验的粗略区间，仅用于横向对比，不作为平台数据）
CATEGORY_RETURN_RATE_BASELINE: dict[str, float] = {
    "服饰": 0.18,
    "女装": 0.20,
    "男装": 0.15,
    "鞋靴": 0.20,
    "箱包": 0.12,
    "美妆": 0.06,
    "护肤": 0.05,
    "数码": 0.08,
    "手机": 0.07,
    "家电": 0.07,
    "食品": 0.03,
    "母婴": 0.09,
    "家居": 0.08,
    "运动户外": 0.13,
}
DEFAULT_RETURN_RATE_BASELINE = 0.10

# 缺陷类别 → 该类缺陷对整体质量分的扣分系数
CATEGORY_PENALTY: dict[str, float] = {
    "材质": 1.0,
    "功能": 1.1,
    "描述不符": 1.3,
    "做工": 0.9,
    "尺码": 0.7,
    "色差": 0.7,
    "物流": 0.4,
    "服务": 0.6,
}

_QUOTE_MAX_CHARS = 60


def is_negative_review(text: str) -> bool:
    """判断一条评价是否属于负面评价。

    Args:
        text: 评价文本。

    Returns:
        是否命中负面语气标记。
    """
    return any(marker in text for marker in NEGATIVE_MARKERS)


def has_defect(text: str) -> bool:
    """判断一条评价是否描述了具体缺陷。

    有些差评不带情绪词（例如「掉色严重」），但已经指出了明确的质量问题，
    这类评价同样应计入差评，否则差评占比会被明显低估。

    Args:
        text: 评价文本。

    Returns:
        是否命中缺陷词库中的任意关键词。
    """
    return any(keyword in text for keyword in DEFECT_LEXICON)


def baseline_return_rate(category: str | None) -> float:
    """查询类目退货率基准。

    Args:
        category: 商品类目。

    Returns:
        基准退货率，未收录的类目返回默认值。
    """
    if not category:
        return DEFAULT_RETURN_RATE_BASELINE
    for key, value in CATEGORY_RETURN_RATE_BASELINE.items():
        if key in category:
            return value
    return DEFAULT_RETURN_RATE_BASELINE


def split_quotes(text: str) -> list[str]:
    """把一条评价按标点切成短句，便于定位命中上下文。

    Args:
        text: 评价原文。

    Returns:
        短句列表（已去除空白）。
    """
    parts = re.split(r"[，,。.!！?？;；\n]+", text)
    return [part.strip() for part in parts if part.strip()]


def extract_defects(reviews: list[str], max_quotes_per_keyword: int = 2) -> list[DefectKeyword]:
    """从评价文本中挖掘缺陷关键词。

    Args:
        reviews: 评价文本列表。
        max_quotes_per_keyword: 每个关键词最多保留的原文片段数。

    Returns:
        缺陷关键词列表，按「出现次数 × 严重度」降序。
    """
    hits: dict[str, DefectKeyword] = {}

    for review in reviews:
        # 用短句定位命中位置，避免整条长评淹没关键信息
        sentences = split_quotes(review) or [review]
        for sentence in sentences:
            for keyword, (category, severity) in DEFECT_LEXICON.items():
                if keyword not in sentence:
                    continue
                item = hits.get(keyword)
                if item is None:
                    item = DefectKeyword(
                        keyword=keyword,
                        category=category,
                        count=0,
                        severity=severity,
                        quotes=[],
                    )
                    hits[keyword] = item
                item.count += 1
                if len(item.quotes) < max_quotes_per_keyword:
                    item.quotes.append(sentence[:_QUOTE_MAX_CHARS])

    # 出现频次越高，实际严重度越高（封顶 1.0）
    for item in hits.values():
        item.severity = round(min(1.0, item.severity * (1 + 0.15 * (item.count - 1))), 3)

    return sorted(hits.values(), key=lambda item: (item.count * item.severity), reverse=True)
