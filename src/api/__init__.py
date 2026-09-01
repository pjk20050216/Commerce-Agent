"""
API 模块。

FastAPI 路由、Schema 和服务层。

Description:
    提供 B 端系统的 RESTful API 接口，包括商品管理、任务管理、资源管理等功能。2026-09-03
"""

from src.api.router import products, tasks, health
from src.api.schema import common, product, task, asset

__all__ = [
    "products",
    "tasks",
    "health",
    "common",
    "product",
    "task",
    "asset",
]
