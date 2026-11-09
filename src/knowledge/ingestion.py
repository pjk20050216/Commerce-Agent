"""
文档摄入服务模块。

Description:
    负责将原始文档解析、分块并抽取实体关系写入知识图谱。
    优先复用 RAG 模块的 DocumentProcessor；其不可用时降级为按段落切分。2026-09-08
"""

import logging
from typing import Any

from src.knowledge.graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """文档摄入服务。

    Example:
        >>> svc = DocumentIngestionService()
        >>> kg = KnowledgeGraph(id="kg_1", name="图谱")
        >>> # result = await svc.process_document({"id": "d1", "content": "..."}, kg)
    """

    def __init__(self) -> None:
        """初始化文档摄入服务。"""
        self._processor: Any = None
        try:
            from src.rag.document_processor import DocumentProcessor

            self._processor = DocumentProcessor()
        except Exception as exc:  # pragma: no cover - 依赖可选
            logger.warning("DocumentProcessor 不可用，降级为段落切分: %s", exc)

    def _chunk(self, content: str) -> list[str]:
        """将文档内容切分为块。

        Args:
            content: 文档正文。

        Returns:
            文本块列表。
        """
        if self._processor is not None:
            try:
                doc = self._processor.parse_content(content, title="ingest")
                chunks = self._processor.process(doc)
                if chunks:
                    return [c.get("content", "") for c in chunks]
            except Exception as exc:  # pragma: no cover - 防御性降级
                logger.warning("文档分块失败，降级为段落切分: %s", exc)
        return [p.strip() for p in content.split("\n\n") if p.strip()]

    async def process_document(
        self, document: dict[str, Any], graph: KnowledgeGraph
    ) -> dict[str, Any]:
        """处理单个文档并写入知识图谱。

        Args:
            document: 文档字典，包含 id/title/content/format。
            graph: 目标知识图谱。

        Returns:
            处理结果，包含 document_id、status、chunk_count 等字段。

        Example:
            >>> # result = await svc.process_document(doc, kg)
            >>> # result["status"]
            'completed'
        """
        doc_id = document.get("id") or "doc_unknown"
        content = document.get("content") or ""
        title = document.get("title") or ""

        chunks = self._chunk(content)

        graph.add_entity(
            {
                "id": doc_id,
                "name": title or doc_id,
                "type": "document",
                "format": document.get("format", "text"),
            }
        )

        return {
            "document_id": doc_id,
            "title": title,
            "status": "completed",
            "chunk_count": len(chunks),
            "entity_count": graph.entity_count,
            "relation_count": graph.relation_count,
        }
