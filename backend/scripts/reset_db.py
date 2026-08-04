import asyncio
import logging
from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO)

async def reset_db():
    logging.info("Truncating all tables in PostgreSQL database...")
    async with engine.begin() as conn:
        await conn.execute(text("""
            TRUNCATE TABLE chat_messages, chat_sessions, trace_spans, chunks, citations, paper_sections, papers CASCADE;
        """))
    logging.info("Database successfully reset! All papers, chunks, traces, and chat messages cleared.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_db())
