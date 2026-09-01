"""Fix tenant_id mismatch: change 'default' to 'dev' in all tables.

The running backend uses tenant_id='dev' (from auth code),
but seed data uses tenant_id='default'. This syncs them.
"""

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
    from src.db.postgres import get_db_session
    from sqlalchemy import text

    tables = [
        "generation_tasks",
        "listing_products",
        "listing_tasks",
        "asset_packages",
        "generated_assets",
        "adapter_configs",
        "task_results",
    ]

    async with get_db_session() as session:
        for table in tables:
            result = await session.execute(
                text(f"UPDATE {table} SET tenant_id = 'dev' WHERE tenant_id = 'default'")
            )
            await session.flush()
            print(f"  {table}: {result.rowcount} rows updated")

        await session.commit()
        print("\nAll tenant_id values updated from 'default' to 'dev'")

    # Verify
    print("\nVerification:")
    async with get_db_session() as session:
        for table in tables:
            result = await session.execute(
                text(f"SELECT tenant_id, count(*) FROM {table} GROUP BY tenant_id")
            )
            rows = result.fetchall()
            for row in rows:
                print(f"  {table}: tenant_id={row[0]}, count={row[1]}")


if __name__ == "__main__":
    asyncio.run(main())
