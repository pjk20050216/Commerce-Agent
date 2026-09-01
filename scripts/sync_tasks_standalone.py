"""Sync tasks from PostgreSQL to Redis using direct DB/Redis access.

This avoids importing src modules (which need cryptography in uv venv).
Uses direct psycopg2 + redis-py calls.
"""

import json
import os
import sys
from datetime import datetime, timezone

import psycopg
import redis

# PostgreSQL connection
pg_conn = psycopg.connect(
    host="127.0.0.1",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="cbcf",
)

# Redis connection
redis_client = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)

PREFIX = "cbcf"
TENANT = "dev"

# Build product id mapping: numeric id -> PROD-XXXX
cur = pg_conn.execute("SELECT id, product_id FROM products WHERE tenant_id = %s", ("default",))
prod_map = {row[0]: row[1] for row in cur.fetchall()}
print(f"Product ID mapping: {len(prod_map)} entries")

# Get all tasks
cur = pg_conn.execute(
    "SELECT task_id, product_id, status, created_at FROM generation_tasks WHERE tenant_id = %s ORDER BY created_at",
    (TENANT,),
)
tasks = cur.fetchall()
print(f"Found {len(tasks)} tasks")

count = 0
for row in tasks:
    task_id, numeric_prod_id, status, created_at = row

    # Map numeric product_id to PROD-XXXX
    mapped_prod_id = prod_map.get(numeric_prod_id, str(numeric_prod_id))

    # Timestamp
    if created_at and isinstance(created_at, datetime):
        timestamp = created_at.timestamp()
        created_at_str = created_at.isoformat()
    else:
        timestamp = datetime.now(timezone.utc).timestamp()
        created_at_str = datetime.now(timezone.utc).isoformat()

    status_val = status or "completed"

    metadata = {
        "task_id": task_id,
        "product_id": mapped_prod_id,
        "tenant_id": TENANT,
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

    task_key = f"{PREFIX}:tenant:{TENANT}:task:{task_id}"
    list_key = f"{PREFIX}:tenant:{TENANT}:task:list"

    pipe = redis_client.pipeline()
    pipe.hset(task_key, mapping={"metadata": json.dumps(metadata, ensure_ascii=False)})
    pipe.zadd(list_key, {task_id: timestamp})
    pipe.execute()

    count += 1

print(f"Synced {count} tasks to Redis")

# Verify
task_count = redis_client.zcard(list_key)
print(f"Redis task list size: {task_count}")

# Test first task
first_id = redis_client.zrevrange(list_key, 0, 0)
if first_id:
    tid = first_id[0]
    meta_raw = redis_client.hget(f"{PREFIX}:tenant:{TENANT}:task:{tid}", "metadata")
    meta = json.loads(meta_raw)
    print(f"  First: {tid} | product={meta.get('product_id')} | status={meta.get('status')}")

pg_conn.close()
redis_client.close()
print("\nDone!")
