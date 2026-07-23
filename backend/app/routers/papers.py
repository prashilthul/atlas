import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import _get_session_factory, get_db
from app.models import Chunk, Paper, PaperSection
from app.schemas import (
    PaperDetailResponse,
    PaperListResponse,
    PaperResponse,
    PaperStatus,
    SectionInfo,
)
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


@router.get("", response_model=PaperListResponse)
async def list_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    year_min: int | None = Query(None),
    year_max: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    conditions = [True]

    if search:
        pattern = f"%{search}%"
        conditions.append(
            Paper.title.ilike(pattern)
            | func.array_to_string(Paper.authors, "|||").ilike(pattern)
        )
    if year_min is not None:
        conditions.append(Paper.year >= year_min)
    if year_max is not None:
        conditions.append(Paper.year <= year_max)

    count_q = select(func.count()).select_from(Paper).where(*conditions)
    total = (await db.execute(count_q)).scalar()

    offset = (page - 1) * page_size
    query = (
        select(Paper)
        .where(*conditions)
        .order_by(Paper.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    papers = (await db.execute(query)).scalars().all()

    paper_ids = [p.id for p in papers]
    section_counts: dict = {}
    chunk_counts: dict = {}

    if paper_ids:
        rows = (
            await db.execute(
                select(PaperSection.paper_id, func.count().label("cnt"))
                .where(PaperSection.paper_id.in_(paper_ids))
                .group_by(PaperSection.paper_id)
            )
        ).all()
        section_counts = {r.paper_id: r.cnt for r in rows}

        rows = (
            await db.execute(
                select(Chunk.paper_id, func.count().label("cnt"))
                .where(Chunk.paper_id.in_(paper_ids))
                .group_by(Chunk.paper_id)
            )
        ).all()
        chunk_counts = {r.paper_id: r.cnt for r in rows}

    items = [
        PaperListItem(
            id=str(p.id),
            title=p.title,
            authors=p.authors,
            year=p.year,
            section_count=section_counts.get(p.id, 0),
            chunk_count=chunk_counts.get(p.id, 0),
            status=p.status,
            created_at=p.created_at.isoformat(),
        )
        for p in papers
    ]

    return PaperListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{paper_id}", response_model=PaperDetailResponse)
async def get_paper(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(404, "Paper not found")

    sections_result = await db.execute(
        select(PaperSection)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.order_index)
    )
    sections = sections_result.scalars().all()

    return PaperDetailResponse(
        id=str(paper.id),
        title=paper.title,
        authors=paper.authors,
        abstract=paper.abstract,
        year=paper.year,
        source_url=paper.source_url,
        status=paper.status,
        created_at=paper.created_at.isoformat(),
        sections=[
            SectionInfo(
                heading=s.heading,
                level=s.level,
                order_index=s.order_index,
            )
            for s in sections
        ],
    )


@router.delete("/{paper_id}", status_code=204)
async def delete_paper(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(404, "Paper not found")
    await db.delete(paper)
    await db.commit()


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
