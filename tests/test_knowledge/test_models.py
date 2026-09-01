"""知识图谱数据模型测试。"""

import pytest
from datetime import datetime
from src.knowledge.graph import KnowledgeGraph
from src.api.schema.knowledge_graph import (
    KnowledgeGraphCreate,
    KnowledgeGraphResponse,
    KnowledgeGraphListResponse,
)


class TestKnowledgeGraph:
    """知识图谱模型测试。"""

    def test_create_knowledge_graph_dataclass(self):
        """测试知识图谱实体模型。"""
        graph = KnowledgeGraph(
            id="kg_001",
            name="产品知识库",
            tenant_id="tenant_001",
            entities=[{"id": "e1", "name": "智能手表"}],
            relations=[{"source": "e1", "target": "e2", "type": "属于"}],
        )
        assert graph.id == "kg_001"
        assert graph.name == "产品知识库"
        assert len(graph.entities) == 1
        assert len(graph.relations) == 1

    def test_knowledge_graph_schemas(self):
        """测试知识图谱 Pydantic Schema。"""
        create_req = KnowledgeGraphCreate(
            name="数码类目图谱",
            description="数码产品知识图谱",
        )
        assert create_req.name == "数码类目图谱"

        now = datetime.now()
        resp = KnowledgeGraphResponse(
            id="kg_002",
            name="服装类目图谱",
            tenant_id="system",
            status="active",
            document_count=5,
            entity_count=20,
            relation_count=15,
            created_at=now,
            updated_at=now,
        )
        assert resp.id == "kg_002"
        assert resp.document_count == 5