-- 多智能体电商购物助手 数据库初始化
-- This script runs automatically when the PostgreSQL container starts for the first time

CREATE EXTENSION IF NOT EXISTS vector;

-- Note: Table creation is handled by SQLAlchemy ORM models
-- See src/db/models.py for table definitions
