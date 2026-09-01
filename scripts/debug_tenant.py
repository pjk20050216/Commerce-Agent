"""Debug tenant_id mismatch between auth and database."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "cbcf")


async def main():
    # 1. What does auth return?
    from src.auth.api_key import require_auth
    from unittest.mock import AsyncMock, MagicMock

    # Create a mock request
    mock_request = MagicMock()
    mock_request.headers = {}

    # Create a mock that works with FastAPI dependency injection
    # Actually, let's just call the inner logic directly
    from src.config.settings import get_settings
    settings = get_settings()
    print(f"auth_enabled: {settings.auth_enabled}")

    # The auth function is async and expects a Request object
    # Let's just test what it returns by constructing a simple mock
    from fastapi import Request
    from starlette.datastructures import MutableHeaders

    scope = {
        "type": "http",
        "headers": [],
    }
    request = Request(scope)

    auth_ctx = await require_auth(request)
    print(f"Auth returns: tenant_id={auth_ctx.tenant_id!r}")

    # 2. What's in the database?
    from src.db.postgres import get_db_session
    from sqlalchemy import text

    tables = ["generation_tasks", "listing_products", "listing_tasks",
              "asset_packages", "generated_assets", "adapter_configs", "task_results"]

    async with get_db_session() as session:
        for table in tables:
            result = await session.execute(
                text(f"SELECT tenant_id, count(*) FROM {table} GROUP BY tenant_id")
            )
            rows = result.fetchall()
            for row in rows:
                print(f"  {table}: tenant_id={row[0]!r}, count={row[1]}")


if __name__ == "__main__":
    asyncio.run(main())
