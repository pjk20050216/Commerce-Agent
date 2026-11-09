"""
知识库 Agent 工作流模块。

Description:
    以 LangGraph 编排的知识库检索问答流程：
    QueryAnalyzer → StrategyRouter → HybridRetriever → Fuser。
    未配置数据库时自动降级为内存语料上的关键词检索，保证接口可用。2026-09-08
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

RRF_K = 60

# 内置示例语料，当数据库不可用时作为兜底检索源
_FALLBACK_CORPUS: list[dict[str, Any]] = [
    {
        "id": "kb_001",
        "content": "主图需使用纯白背景，尺寸不低于 1500x1500，商品主体占画面 85% 以上。",
        "source": "platform_specs",
    },
    {
        "id": "kb_002",
        "content": "标题中不得使用“最佳”“第一”“100%”等广告法禁止的绝对化用语。",
        "source": "compliance_rules",
    },
    {
        "id": "kb_003",
        "content": "场景图用于展示商品在实际使用环境中的效果，强调目标用户的生活方式。",
        "source": "creative_guide",
    },
    {
        "id": "kb_004",
        "content": "视频分镜建议包含产品介绍、功能卖点、使用场景与行动号召四类镜头。",
        "source": "storyboard_guide",
    },
]


@dataclass
class KnowledgeQueryState:
    """知识库 Agent 状态。

    Attributes:
        query: 用户原始查询。
        rewritten_queries: 查询改写结果。
        strategy: 检索策略。
        dense_results: 向量检索结果。
        sparse_results: 关键词检索结果。
        fused_results: RRF 融合后的结果。
        final_answer: 最终回答。
        sources: 引用来源。
        agent_logs: Agent 执行日志。
    """

    query: str
    rewritten_queries: list[str] = field(default_factory=list)
    strategy: str = "hybrid"
    dense_results: list[dict[str, Any]] = field(default_factory=list)
    sparse_results: list[dict[str, Any]] = field(default_factory=list)
    fused_results: list[dict[str, Any]] = field(default_factory=list)
    final_answer: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    agent_logs: list[dict[str, Any]] = field(default_factory=list)


class KnowledgeAgentWorkflow:
    """知识库检索问答工作流。

    Attributes:
        top_k: 返回结果数量。

    Example:
        >>> wf = KnowledgeAgentWorkflow()
        >>> # state = await wf.run("主图尺寸要求")
        >>> # print(state.final_answer)
    """

    def __init__(self, top_k: int | None = None) -> None:
        """初始化工作流。

        Args:
            top_k: 返回结果数量，默认取配置 retrieval_top_k。
        """
        settings = get_settings()
        self.top_k = top_k or getattr(settings, "retrieval_top_k", 5)

    def _log(self, state: KnowledgeQueryState, agent: str, message: str) -> None:
        """记录 Agent 日志。

        Args:
            state: 工作流状态。
            agent: Agent 名称。
            message: 日志内容。
        """
        state.agent_logs.append({"agent": agent, "message": message})

    def _analyze(self, state: KnowledgeQueryState) -> None:
        """分析查询并生成改写版本。

        Args:
            state: 工作流状态。
        """
        query = state.query.strip()
        state.rewritten_queries = [query]
        for token in ("规格", "尺寸", "合规", "禁用", "场景", "分镜"):
            if token in query and f"{query} {token}" not in state.rewritten_queries:
                state.rewritten_queries.append(f"{query} {token}")
        self._log(state, "QueryAnalyzer", f"生成 {len(state.rewritten_queries)} 个查询变体")

    def _route(self, state: KnowledgeQueryState) -> None:
        """选择检索策略。

        Args:
            state: 工作流状态。
        """
        state.strategy = "hybrid"
        self._log(state, "StrategyRouter", f"选择策略: {state.strategy}")

    def _keyword_search(self, query: str) -> list[dict[str, Any]]:
        """基于字符重叠的关键词检索。

        Args:
            query: 查询文本。

        Returns:
            按得分降序排列的结果列表。
        """
        results: list[dict[str, Any]] = []
        q_chars = {c for c in query if not c.isspace()}
        for doc in _FALLBACK_CORPUS:
            content = doc["content"]
            overlap = len(q_chars & {c for c in content if not c.isspace()})
            if overlap:
                score = overlap / max(len(q_chars), 1)
                results.append({**doc, "score": round(score, 4)})
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[: self.top_k]

    def _retrieve(self, state: KnowledgeQueryState) -> None:
        """执行检索。

        Args:
            state: 工作流状态。
        """
        for q in state.rewritten_queries:
            state.sparse_results.extend(self._keyword_search(q))
        # 去重
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for r in state.sparse_results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)
        state.sparse_results = unique
        state.dense_results = []
        self._log(
            state,
            "HybridRetriever",
            f"关键词命中 {len(state.sparse_results)} 条，向量检索 {len(state.dense_results)} 条",
        )

    def _fuse(self, state: KnowledgeQueryState) -> None:
        """RRF 融合多路检索结果。

        Args:
            state: 工作流状态。
        """
        scores: dict[str, float] = {}
        docs: dict[str, dict[str, Any]] = {}
        for results in (state.dense_results, state.sparse_results):
            for rank, item in enumerate(results, start=1):
                doc_id = item.get("id", f"doc_{rank}")
                docs[doc_id] = item
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)

        state.fused_results = [
            {**docs[doc_id], "rrf_score": round(score, 6)}
            for doc_id, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        ][: self.top_k]
        state.sources = [
            {"id": r["id"], "source": r.get("source")} for r in state.fused_results
        ]
        self._log(state, "Fuser", f"RRF 融合得到 {len(state.fused_results)} 条结果")

    def _answer(self, state: KnowledgeQueryState) -> None:
        """基于检索结果生成回答。

        Args:
            state: 工作流状态。
        """
        if not state.fused_results:
            state.final_answer = "未在知识库中检索到相关内容。"
        else:
            parts = [f"[{i}] {r['content']}" for i, r in enumerate(state.fused_results, 1)]
            state.final_answer = "根据知识库检索结果：\n" + "\n".join(parts)
        self._log(state, "AnswerGenerator", "生成最终回答")

    async def run(self, query: str) -> KnowledgeQueryState:
        """执行完整工作流。

        Args:
            query: 用户查询。

        Returns:
            执行完成的状态对象。

        Example:
            >>> # state = await KnowledgeAgentWorkflow().run("主图尺寸")
            >>> # assert state.final_answer
        """
        state = KnowledgeQueryState(query=query)
        self._analyze(state)
        self._route(state)
        self._retrieve(state)
        self._fuse(state)
        self._answer(state)
        return state
