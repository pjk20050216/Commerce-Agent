import asyncio,os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("POSTGRES_HOST","127.0.0.1")
os.environ.setdefault("POSTGRES_PORT","5432")
os.environ.setdefault("POSTGRES_USER","postgres")
os.environ.setdefault("POSTGRES_PASSWORD","postgres")
os.environ.setdefault("POSTGRES_DB","cbcf")
async def main():
    from src.db.postgres import get_db_session
    from sqlalchemy import text
    tables=["generation_tasks","listing_products","listing_tasks","asset_packages","generated_assets","adapter_configs","task_results"]
    async with get_db_session() as s:
        for t in tables:
            r=await s.execute(text(f"UPDATE {t} SET tenant_id='dev' WHERE tenant_id='default'"))
            await s.flush()
            print(f"{t}: {r.rowcount}")
        await s.commit()
    print("Done")
asyncio.run(main())
