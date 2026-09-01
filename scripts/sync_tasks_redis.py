"""Sync generation tasks from PostgreSQL to Redis for API consumption.

The tasks API reads from Redis via RedisClient.list_tasks(),
but seed data was populated in PostgreSQL. This bridges the gap.

Uses the Redis client's internal key structure:
  - {prefix}:{tenant}:task:{task_id}  -> hash with "metadata" field (JSON)
  - {prefix}:{tenant}:task:list       -> zset of task_ids by timestamp
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "cbcf")


async def main():
    from src.api.service.redis_client import get_redis
    from src.db.postgres import get_db_session
    from src.db.models import GenerationTask as TaskPO
    from sqlalchemy import select

    redis = await get_redis()
    await redis._ensure_connected()

    tenant_id = "dev"

    async with get_db_session() as session:
        result = await session.execute(
            select(TaskPO).where(TaskPO.tenant_id == tenant_id)
        )
        tasks = result.scalars().all()
        print(f"Found {len(tasks)} tasks in PostgreSQL for tenant_id='{tenant_id}'")

        count = 0
        error_count = 0

        for po in tasks:
            try:
                task_id = po.task_id
                product_id = getattr(po, "product_id", "") or ""

                # Get timestamps safely
                created_at = getattr(po, "created_at", None)
                if created_at and isinstance(created_at, datetime):
                    timestamp = created_at.timestamp()
                    created_at_str = created_at.isoformat()
                else:
                    timestamp = datetime.now(timezone.utc).timestamp()
                    created_at_str = datetime.now(timezone.utc).isoformat()

                status_val = getattr(po, "status", "completed") or "completed"

                metadata = {
                    "task_id": task_id,
                    "product_id": product_id,
                    "tenant_id": tenant_id,
                    "status": status_val,
                    "progress": 100.0 if status_val == "completed" else 0.0,
                    "current_step": "completed" if status_val == "completed" else "init",
                    "created_at": created_at_str,
                    "updated_at": created_at_str,
                    "request": {
                        "task_id": task_id,
                        "task_type": "image_and_video",
                        "image_types": ["main", "scene"],
                        "image_count_per_type": 1,
                        "video_duration": 30.0,
                        "video_style": "professional",
                        "style_preference": None,
                        "color_preference": None,
                        "quality_level": "standard",
                    },
                }

                # Use internal Redis key structure matching the client
                task_key = redis._tenant_key(tenant_id, "task", task_id)
                list_key = redis._tenant_key(tenant_id, "task", "list")

                async with redis._client.pipeline() as pipe:
                    pipe.hset(task_key, mapping={"metadata": json.dumps(metadata, ensure_ascii=False)})
                    pipe.zadd(list_key, {task_id: timestamp})
                    await pipe.execute()

                count += 1
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    print(f"  Error on {getattr(po, 'task_id', '?')}: {e}")

        print(f"Synced {count} tasks to Redis ({error_count} errors)")

    # Verify
    items, total = await redis.list_tasks(tenant_id=tenant_id, page_size=3)
    print(f"\nRedis list_tasks: {total} total, {len(items)} items on page 1")

    if items:
        item = items[0]
        print(f"  First: task_id={item.get('task_id')} | product_id={item.get('product_id')} | status={item.get('status')}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
