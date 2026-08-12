import asyncio
import logging

from sqlalchemy import select, update

from app.database import _get_session_factory
from app.models import Chunk, Paper
from app.services.embedder import embed_texts

logging.basicConfig(level=logging.INFO)


async def reembed_papers() -> None:
    async with _get_session_factory()() as db:
        papers = (
            await db.execute(select(Paper).where(Paper.status == "ready"))
        ).scalars().all()
        for paper in papers:
            rows = (
                await db.execute(
                    select(Chunk.id, Chunk.content).where(Chunk.paper_id == paper.id)
                )
            ).all()
            if not rows:
                continue
            logging.info("Re-embedding %d chunks for paper %s", len(rows), paper.title[:50])
            vectors = embed_texts([content for _, content in rows])
            for (chunk_id, _), vector in zip(rows, vectors):
                await db.execute(
                    update(Chunk).where(Chunk.id == chunk_id).values(embedding=vector)
                )
            await db.commit()
            logging.info("Finished paper %s", paper.title[:50])
    logging.info("Re-embedding complete")


if __name__ == "__main__":
    asyncio.run(reembed_papers())
