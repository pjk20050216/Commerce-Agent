"""
知识图谱模型模块。

Description:
    定义轻量级知识图谱的内存表示，包含实体与关系，
    用于知识库文档摄入后的结构化存储。2026-09-08
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class KnowledgeGraph:
    """内存知识图谱。

    Attributes:
        id: 图谱唯一标识。
        name: 图谱名称。
        tenant_id: 所属租户。
        entities: 实体列表。
        relations: 关系列表。
        created_at: 创建时间。
        updated_at: 更新时间。

    Example:
        >>> kg = KnowledgeGraph(id="kg_001", name="产品知识库", tenant_id="t1")
        >>> kg.add_entity({"id": "e1", "name": "智能手表"})
        >>> kg.entity_count
        1
    """

    id: str
    name: str
    tenant_id: str = "system"
    entities: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_entity(self, entity: dict[str, Any]) -> None:
        """添加实体（按 id 去重）。

        Args:
            entity: 实体字典，至少包含 id 字段。
        """
        entity_id = entity.get("id")
        if entity_id and any(e.get("id") == entity_id for e in self.entities):
            return
        self.entities.append(entity)
        self.updated_at = datetime.now()

    def add_relation(self, relation: dict[str, Any]) -> None:
        """添加关系。

        Args:
            relation: 关系字典，包含 source/target/type 字段。
        """
        self.relations.append(relation)
        self.updated_at = datetime.now()

    @property
    def entity_count(self) -> int:
        """实体数量。

        Returns:
            实体个数。
        """
        return len(self.entities)

    @property
    def relation_count(self) -> int:
        """关系数量。

        Returns:
            关系个数。
        """
        return len(self.relations)
