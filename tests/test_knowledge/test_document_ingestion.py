"""文档摄入服务测试。"""

import pytest
from src.knowledge.ingestion import DocumentIngestionService
from src.knowledge.graph import KnowledgeGraph
from src.rag.document_processor import DocumentProcessor


class TestDocumentIngestionService:
    """文档摄入服务测试。"""

    @pytest.fixture
    def service(self):
        """创建服务实例。"""
        return DocumentIngestionService()

    def test_service_initialization(self, service):
        """测试服务初始化。"""
        assert service is not None

    @pytest.mark.asyncio
    async def test_process_document(self, service):
        """测试完整文档处理流程。"""
        document = {
            "id": "doc_001",
            "title": "测试文档",
            "content": "这是一个测试文档内容，用于验证文档处理流程。",
            "format": "markdown",
        }
        graph = KnowledgeGraph(
            id="kg_001",
            name="测试图谱",
            tenant_id="tenant_001",
        )

        result = await service.process_document(document, graph)
        assert result is not None
        assert result["document_id"] == "doc_001"
        assert result["status"] == "completed"


class TestDocumentProcessor:
    """RAG 文档处理器测试。"""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_parse_content(self, processor):
        content = "# 产品说明\n\n这是一个智能手表产品。\n\n## 功能特点\n- 心率监测\n- GPS 定位\n"
        doc = processor.parse_content(content, title="产品说明", doc_type="product")
        assert doc.title == "产品说明"
        assert "心率监测" in doc.content

    def test_process_chunks(self, processor):
        content = "段落一：智能运动手表具备心率监测功能。\n\n段落二：超长续航支持14天待机。"
        doc = processor.parse_content(content, title="测试分块")
        chunks = processor.process(doc)
        assert len(chunks) >= 1
        assert chunks[0]["metadata"]["title"] == "测试分块"