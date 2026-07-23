import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import _get_session_factory, get_db
from app.models import Chunk, Paper, PaperSection
from app.schemas import PaperResponse, PaperStatus
from app.services.chunker import ChunkData, chunk_sections
from app.services.embedder import embed_chunks
from app.services.parser import parse_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.post("/upload", response_model=PaperResponse, status_code=201)
async def upload_paper(
    file: UploadFile = File(...),
    bg_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    if not _is_pdf(file):
        raise HTTPException(400, "Only PDF files are accepted")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    paper_schema = parse_pdf(stream=content)

    paper = Paper(
        title=paper_schema.title,
        authors=paper_schema.authors,
        abstract=paper_schema.abstract,
        year=paper_schema.year,
        source_url=paper_schema.source_url,
        status="processing",
    )
    db.add(paper)
    await db.flush()

    section_records = []
    for sec_schema in paper_schema.sections:
        sec = PaperSection(
            paper_id=paper.id,
            heading=sec_schema.heading,
            level=sec_schema.level,
            content=sec_schema.content,
            order_index=sec_schema.order_index,
        )
        db.add(sec)
        section_records.append(sec)
    await db.flush()

    heading_to_section_id = {}
    for sec_schema, sec_record in zip(paper_schema.sections, section_records):
        heading_to_section_id[sec_schema.heading] = sec_record.id

    chunk_data_list = chunk_sections(paper_schema.sections, str(paper.id))

    placeholder = [0.0] * 768
    for cd in chunk_data_list:
        chunk = Chunk(
            paper_id=paper.id,
            section_id=heading_to_section_id.get(cd.section_heading),
            content=cd.content,
            embedding=placeholder,
            meta_data={
                "section_heading": cd.section_heading,
                "section_level": cd.section_level,
                "chunk_index": cd.chunk_index,
                "total_sections": cd.total_sections,
            },
        )
        db.add(chunk)

    await db.commit()

    bg_tasks.add_task(_embed_and_update, paper.id)

    return PaperResponse(
        id=str(paper.id),
        title=paper.title,
        authors=paper.authors,
        chunk_count=len(chunk_data_list),
        status="processing",
    )


@router.get("/{paper_id}/status", response_model=PaperStatus)
async def get_paper_status(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(404, "Paper not found")
    return PaperStatus(
        id=str(paper.id),
        status=paper.status,
        error=paper.error_message,
    )


async def _embed_and_update(paper_id: UUID) -> None:
    factory = _get_session_factory()
    async with factory() as db:
        try:
            result = await db.execute(
                select(Chunk).where(Chunk.paper_id == paper_id).order_by(Chunk.id)
            )
            chunks = result.scalars().all()

            chunk_data_list = [
                ChunkData(
                    paper_id=str(c.paper_id),
                    section_heading=c.meta_data.get("section_heading", ""),
                    section_level=c.meta_data.get("section_level", 0),
                    content=c.content,
                    chunk_index=c.meta_data.get("chunk_index", 0),
                    total_sections=c.meta_data.get("total_sections", 0),
                )
                for c in chunks
            ]

            embeddings = embed_chunks(chunk_data_list)

            for chunk, emb in zip(chunks, embeddings):
                stmt = update(Chunk).where(Chunk.id == chunk.id).values(embedding=emb)
                await db.execute(stmt)

            stmt = update(Paper).where(Paper.id == paper_id).values(status="ready")
            await db.execute(stmt)
            await db.commit()

            logger.info("Embedding complete for paper %s", paper_id)
        except Exception:
            logger.exception("Embedding failed for paper %s", paper_id)
            stmt = (
                update(Paper)
                .where(Paper.id == paper_id)
                .values(status="error", error_message="Embedding pipeline failed")
            )
            await db.execute(stmt)
            await db.commit()


def _is_pdf(file: UploadFile) -> bool:
    if file.content_type == "application/pdf":
        return True
    if file.filename and file.filename.lower().endswith(".pdf"):
        return True
    return False
