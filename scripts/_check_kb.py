"""Check knowledge base status in database."""
import asyncio
from src.db.postgres import get_db_session
from sqlalchemy import text


async def check():
    async with get_db_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM knowledge_docs"))
        doc_count = result.scalar()
        print(f"knowledge_docs: {doc_count}")

        result = await session.execute(text("SELECT COUNT(*) FROM knowledge_chunks"))
        chunk_count = result.scalar()
        print(f"knowledge_chunks: {chunk_count}")

        if doc_count > 0:
            result = await session.execute(
                text(
                    "SELECT doc_type, COUNT(*) FROM knowledge_docs "
                    "GROUP BY doc_type ORDER BY doc_type"
                )
            )
            for row in result:
                print(f"  {row[0]}: {row[1]}")

            result = await session.execute(
                text("SELECT id, title, doc_type FROM knowledge_docs LIMIT 10")
            )
            for row in result:
                print(f"  [{row[0]}] {row[2]}: {row[1][:80]}")


asyncio.run(check())
