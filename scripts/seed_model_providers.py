"""
模型厂商预置数据脚本。

Description:
    为指定租户写入预置的模型厂商配置（阿里云、商汤、可灵等）。
    该逻辑原先以 ``python -c`` 单行命令内联在 setup_all.bat 中，
    但 ``async def`` 属于复合语句，无法跟在分号后，导致该步骤始终失败。
    此处改为独立脚本，便于维护与单独执行。

Usage:
    uv run python scripts/seed_model_providers.py [tenant_id]

Example:
    >>> # uv run python scripts/seed_model_providers.py system
"""

import asyncio
import sys

from src.db.model_provider_seeder import seed_model_providers
from src.db.postgres import get_db_session


async def main(tenant_id: str) -> int:
    """为指定租户写入预置厂商配置。

    Args:
        tenant_id: 租户 ID。

    Returns:
        进程退出码，0 表示成功。
    """
    async with get_db_session() as session:
        await seed_model_providers(session, tenant_id)
        await session.commit()
    print(f"模型厂商数据完成 (tenant={tenant_id})")
    return 0


if __name__ == "__main__":
    tid = sys.argv[1] if len(sys.argv) > 1 else "system"
    raise SystemExit(asyncio.run(main(tid)))
