"""创建 User/Tenant 表并插入开发测试用户。

运行: C:/Users/JT/.conda/envs/cbcf/python.exe scripts/migrate_users.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime

import asyncpg

os.environ["PYTHONIOENCODING"] = "utf-8"


async def main() -> None:
    conn = await asyncpg.connect(
        host="127.0.0.1", port=5432, user="postgres", password="postgres", database="cbcf"
    )

    # 创建 tenants 表
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            owner_user_id INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    print("[OK] tenants table ready")

    # 创建 tenant_id 索引
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tenants_tenant_id ON tenants(tenant_id)
    """)

    # 创建 users 表
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            tenant_id VARCHAR(100) NOT NULL,
            display_name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    print("[OK] users table ready")

    # 创建 users 索引
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id)
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
    """)

    # 检查是否已有 dev tenant
    existing = await conn.fetchrow(
        "SELECT id FROM tenants WHERE tenant_id = 'dev'"
    )
    if not existing:
        await conn.execute(
            """INSERT INTO tenants (tenant_id, name, is_active, created_at, updated_at)
               VALUES ('dev', '开发工作空间', TRUE, NOW(), NOW())"""
        )
        print("[OK] Dev tenant created (tenant_id='dev')")
    else:
        print("[OK] Dev tenant already exists")

    # 创建开发用户 (密码: admin123)
    import hashlib
    import secrets

    existing_user = await conn.fetchrow(
        "SELECT id FROM users WHERE username = 'admin'"
    )
    if not existing_user:
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", "admin123".encode(), salt.encode(), 600_000)
        password_hash = f"pbkdf2:sha256:600000:{salt}:{dk.hex()}"

        await conn.execute(
            """INSERT INTO users (username, password_hash, tenant_id, display_name, is_active, created_at, updated_at)
               VALUES ('admin', $1, 'dev', '管理员', TRUE, NOW(), NOW())""",
            password_hash,
        )
        print("[OK] Dev user created: admin / admin123")
    else:
        print("[OK] Dev user already exists")

    # 验证
    tenant_count = await conn.fetchval("SELECT count(*) FROM tenants")
    user_count = await conn.fetchval("SELECT count(*) FROM users")
    print(f"\nDone: {tenant_count} tenants, {user_count} users")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
