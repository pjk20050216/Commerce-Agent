"""
风格顾问 Agent。

Description:
    从用户历史浏览/收藏/加购/购买记录中提取审美偏好，形成风格画像，
    并给出候选商品与画像的匹配分。

    实现要点：
    - 行为权重：浏览 < 收藏 < 加购 < 购买，加购与购买才真正代表偏好；
    - 风格识别使用可解释的关键词映射，而不是让 LLM 凭空总结，
      这样「为什么判你是极简风」始终能指回具体商品；
    - LLM 仅在生成画像摘要时可选参与，缺 Key 时用规则文案兜底。
2026-11-09
"""

import logging
from collections import Counter
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentResult, AgentRole
from src.agents.consumer_base import ConsumerAgentBase
from src.graph.buyer_state import BuyerState
from src.models.buyer import (
    AgentTraceItem,
    BrowsingAction,
    BrowsingRecord,
    CandidateProduct,
    PriceBand,
    StyleDimension,
    StyleProfile,
)

logger = logging.getLogger(__name__)

# 风格 → 判定关键词（命中标题/标签/类目即计入）
STYLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "极简风": ("极简", "简约", "基础款", "纯色", "无logo", "素色", "百搭", "clean fit"),
    "高街潮牌": ("高街", "潮牌", "街头", "oversize", "宽松", "印花", "联名", "工装"),
    "法式复古": ("法式", "复古", "碎花", "泡泡袖", "收腰", "方领", "茶歇"),
    "新中式": ("国风", "新中式", "汉服", "盘扣", "刺绣", "香云纱", "马面裙"),
    "运动机能": ("运动", "机能", "户外", "冲锋", "速干", "防晒", "瑜伽"),
    "甜美少女": ("甜美", "少女", "仙女", "蕾丝", "蝴蝶结", "蓬蓬", "粉色"),
    "商务正装": ("商务", "西装", "正装", "衬衫", "领带", "通勤", "职业"),
    "辣妹性感": ("辣妹", "性感", "紧身", "露腰", "吊带", "包臀"),
    "精致轻奢": ("轻奢", "小香", "质感", "真皮", "羊毛", "羊绒", "垂坠"),
}

# 不同行为的偏好强度
ACTION_WEIGHT: dict[BrowsingAction, float] = {
    BrowsingAction.VIEW: 1.0,
    BrowsingAction.FAVORITE: 2.0,
    BrowsingAction.CART: 3.0,
    BrowsingAction.PURCHASE: 4.0,
}

ACTION_LABEL: dict[BrowsingAction, str] = {
    BrowsingAction.VIEW: "浏览",
    BrowsingAction.FAVORITE: "收藏",
    BrowsingAction.CART: "加购",
    BrowsingAction.PURCHASE: "购买",
}

# 达到该样本量时画像置信度记为满分
CONFIDENT_SAMPLE_SIZE = 20


class StyleAdvisorAgent(ConsumerAgentBase[BuyerState]):
    """风格顾问 Agent。

    Example:
        >>> advisor = StyleAdvisorAgent(enable_llm=False)
        >>> profile = await advisor.build_profile("u1", records, candidate)
        >>> profile.dominant_styles[0].name
        '极简风'
    """

    def __init__(self, enable_llm: bool = True, **kwargs: Any) -> None:
        """初始化风格顾问。

        Args:
            enable_llm: 是否允许调用 LLM 优化画像摘要。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(
            role=AgentRole.BUYER_STYLE_ADVISOR,
            enable_llm=enable_llm,
            **kwargs,
        )
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """注册提示模板。"""
        self.register_prompt(
            "profile_summary",
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是一名资深时尚买手。请根据用户的商品浏览与购买记录，"
                        "用一句话（不超过 60 字）概括其审美偏好，"
                        "并补充一条最具操作性的选品建议。"
                        "只输出这句话，不要分点、不要解释推理过程。",
                    ),
                    (
                        "human",
                        "用户行为记录：\n{records}\n\n"
                        "价格带：{price_band}\n"
                        "规则识别的风格：{styles}\n\n"
                        "请输出画像概括。",
                    ),
                ]
            ),
        )

    # ------------------------------------------------------------------
    # 核心：画像构建
    # ------------------------------------------------------------------
    async def build_profile(
        self,
        user_id: str,
        records: list[BrowsingRecord],
        candidate: CandidateProduct | None = None,
    ) -> StyleProfile:
        """构建用户风格画像。

        Args:
            user_id: 用户 ID。
            records: 历史行为记录。
            candidate: 候选商品（用于填充价格带中的 preferred_price）。

        Returns:
            风格画像。
        """
        style_scores, evidence = self._accumulate_styles(records)
        dominant = self._to_dimensions(style_scores, evidence)
        price_band = self._build_price_band(records, candidate)
        categories = self._top_values([record.category for record in records], limit=3)
        brands = self._top_values([record.brand for record in records], limit=3)
        confidence = min(1.0, round(len(records) / CONFIDENT_SAMPLE_SIZE, 2))

        summary = self._rule_summary(dominant, price_band, categories, len(records))
        if records:
            llm_summary = await self.try_generate(
                self.get_prompt("profile_summary"),
                {
                    "records": self._format_records(records),
                    "price_band": self._format_price_band(price_band),
                    "styles": "、".join(f"{item.name}({item.weight:.0%})" for item in dominant)
                    or "无明显偏好",
                },
                accept=lambda text: len(text) <= 200,
            )
            if llm_summary:
                summary = llm_summary

        return StyleProfile(
            user_id=user_id,
            dominant_styles=dominant,
            price_band=price_band,
            preferred_categories=categories,
            brand_affinity=brands,
            confidence=confidence,
            based_on_records=len(records),
            summary=summary,
        )

    def _accumulate_styles(
        self, records: list[BrowsingRecord]
    ) -> tuple[dict[str, float], dict[str, list[str]]]:
        """累加各风格命中得分。

        Args:
            records: 历史行为记录。

        Returns:
            ``(风格得分, 风格证据)`` 二元组。
        """
        scores: dict[str, float] = {}
        evidence: dict[str, list[str]] = {}

        for record in records:
            text = " ".join(
                [
                    record.title or "",
                    " ".join(record.tags),
                    record.category or "",
                ]
            ).lower()
            weight = ACTION_WEIGHT.get(record.action, 1.0)

            for style, keywords in STYLE_KEYWORDS.items():
                matched = sum(1 for keyword in keywords if keyword.lower() in text)
                if not matched:
                    continue
                scores[style] = scores.get(style, 0.0) + weight * matched
                quotes = evidence.setdefault(style, [])
                if len(quotes) < 3:
                    label = ACTION_LABEL.get(record.action, "浏览")
                    quotes.append(f"{label} · {record.title[:24]}")

        return scores, evidence

    def _to_dimensions(
        self, scores: dict[str, float], evidence: dict[str, list[str]]
    ) -> list[StyleDimension]:
        """把得分归一化为风格维度列表。

        Args:
            scores: 风格得分。
            evidence: 风格证据。

        Returns:
            按权重降序的风格维度列表。
        """
        total = sum(scores.values())
        if total <= 0:
            return []

        dimensions = [
            StyleDimension(
                name=style,
                weight=round(score / total, 3),
                evidence=evidence.get(style, []),
            )
            for style, score in scores.items()
        ]
        dimensions.sort(key=lambda item: item.weight, reverse=True)
        # 只保留占比 >= 5% 的风格，避免长尾噪音
        return [item for item in dimensions if item.weight >= 0.05][:5]

    def _build_price_band(
        self, records: list[BrowsingRecord], candidate: CandidateProduct | None
    ) -> PriceBand:
        """计算价格带画像。

        Args:
            records: 历史行为记录。
            candidate: 候选商品。

        Returns:
            价格带画像。
        """
        prices = [record.price for record in records if record.price is not None]
        band = PriceBand(preferred_price=candidate.price if candidate else None)
        if prices:
            band.min_price = min(prices)
            band.max_price = max(prices)
            band.avg_price = round(sum(prices) / len(prices), 2)
        return band

    @staticmethod
    def _top_values(values: list[str | None], limit: int = 3) -> list[str]:
        """统计出现次数最多的取值。

        Args:
            values: 原始取值列表，可能含 None。
            limit: 保留数量。

        Returns:
            高频取值列表。
        """
        counter = Counter(value for value in values if value)
        return [item for item, _ in counter.most_common(limit)]

    # ------------------------------------------------------------------
    # 风格匹配
    # ------------------------------------------------------------------
    def score_fit(
        self, profile: StyleProfile, candidate: CandidateProduct
    ) -> tuple[float, list[str]]:
        """计算候选商品与用户画像的匹配分。

        口径：基础分 50；命中用户偏好风格时按该风格权重加分
        （权重 0.6 的极简风命中 → +60，直接打满）；完全没有命中时轻微扣分。

        Args:
            profile: 风格画像。
            candidate: 候选商品。

        Returns:
            ``(匹配分 0-100, 依据列表)``。
        """
        if not profile.dominant_styles:
            return 60.0, ["用户行为样本不足，风格匹配按中性 60 分处理"]

        text = " ".join(
            [candidate.title, " ".join(candidate.tags), candidate.category or ""]
        ).lower()

        matched_weight = 0.0
        reasons: list[str] = []
        for dimension in profile.dominant_styles:
            keywords = STYLE_KEYWORDS.get(dimension.name, ())
            if not keywords:
                continue
            hits = [keyword for keyword in keywords if keyword.lower() in text]
            if not hits:
                continue
            matched_weight += dimension.weight
            reasons.append(
                f"命中偏好风格「{dimension.name}」（权重 {dimension.weight:.0%}）："
                f"{'、'.join(hits[:3])}"
            )

        score = 50.0 + matched_weight * 100.0
        score = round(max(0.0, min(100.0, score)), 2)

        if not reasons:
            top = profile.dominant_styles[0]
            reasons.append(f"未命中偏好风格「{top.name}」相关关键词，风格分按 50 分处理")

        # 价格带偏离提示（不直接扣风格分，但作为决策依据暴露出去）
        band = profile.price_band
        if band.min_price is not None and band.max_price is not None:
            if candidate.price < band.min_price * 0.6:
                reasons.append(
                    f"价格 ¥{candidate.price:.0f} 明显低于你的常用价格带 "
                    f"¥{band.min_price:.0f}-¥{band.max_price:.0f}，留意品质预期落差"
                )
            elif candidate.price > band.max_price * 1.5:
                reasons.append(
                    f"价格 ¥{candidate.price:.0f} 高于你的常用价格带 "
                    f"¥{band.min_price:.0f}-¥{band.max_price:.0f}，属于消费升级款"
                )

        return score, reasons

    # ------------------------------------------------------------------
    # 文案
    # ------------------------------------------------------------------
    def _rule_summary(
        self,
        dominant: list[StyleDimension],
        band: PriceBand,
        categories: list[str],
        record_count: int,
    ) -> str:
        """生成规则版画像摘要。

        Args:
            dominant: 风格维度。
            band: 价格带。
            categories: 高频类目。
            record_count: 样本量。

        Returns:
            画像摘要文本。
        """
        if record_count == 0:
            return "暂无行为样本，先记录几次浏览/收藏，画像会逐步变准。"

        parts: list[str] = []
        if dominant:
            top = dominant[0]
            parts.append(f"偏好「{top.name}」（占 {top.weight:.0%}）")
        if band.min_price is not None and band.max_price is not None:
            parts.append(f"常买价位 ¥{band.min_price:.0f}-¥{band.max_price:.0f}")
        if categories:
            parts.append(f"高频类目 {'、'.join(categories)}")
        parts.append(f"基于 {record_count} 条行为记录")
        return "，".join(parts) + "。"

    @staticmethod
    def _format_records(records: list[BrowsingRecord]) -> str:
        """把行为记录格式化为提示词输入。

        Args:
            records: 行为记录。

        Returns:
            多行文本。
        """
        lines: list[str] = []
        for record in records[:30]:
            label = ACTION_LABEL.get(record.action, "浏览")
            tags = "、".join(record.tags[:4]) or "无标签"
            price = f"¥{record.price:.0f}" if record.price is not None else "价格未知"
            lines.append(f"- {label}：{record.title}（{tags}，{price}）")
        return "\n".join(lines) if lines else "无"

    @staticmethod
    def _format_price_band(band: PriceBand) -> str:
        """把价格带格式化为提示词输入。

        Args:
            band: 价格带。

        Returns:
            文本描述。
        """
        if band.min_price is None or band.max_price is None:
            return "未知"
        return f"¥{band.min_price:.0f}-¥{band.max_price:.0f}（均价 ¥{band.avg_price or 0:.0f}）"

    # ------------------------------------------------------------------
    # 工作流接口
    # ------------------------------------------------------------------
    async def execute(self, state: BuyerState) -> AgentResult:
        """执行画像构建与匹配（工作流节点接口）。

        Args:
            state: 买手团状态。

        Returns:
            包含风格画像与匹配分的结果。
        """
        try:
            profile = await self.build_profile(
                user_id=state.user_id,
                records=state.history,
                candidate=state.candidate,
            )
            fit, reasons = self.score_fit(profile, state.candidate)
            state.style_profile = profile
            state.style_fit = fit
            state.style_reasons = reasons

            return AgentResult(
                success=True,
                data={
                    "style_profile": profile.model_dump(mode="json"),
                    "style_fit": fit,
                    "style_reasons": reasons,
                    "agent_trace": AgentTraceItem(
                        agent=self.role.value,
                        status="completed",
                        detail=f"识别风格 {len(profile.dominant_styles)} 个，"
                        f"样本 {profile.based_on_records} 条，匹配分 {fit:.0f}",
                    ).model_dump(),
                },
            )
        except Exception as exc:  # 单路失败不阻断整体决策
            logger.exception("风格顾问执行失败")
            return AgentResult(success=False, error=f"风格画像构建失败: {exc}")
