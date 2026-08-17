import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import _get_session_factory, get_db
from app.models import ChatMessage, ChatSession
from app.services.generator import generate, stream_generate
from app.services.online_eval import run_online_eval
from app.services.query_rewriter import rewrite_query, should_rewrite
from app.services.reranker import rerank
from app.services.retriever import retrieve
from app.services.tracing import Tracer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    paper_ids: list[str] | None = None
    session_id: str | None = None
    stream: bool = False
    evaluate: bool | None = None
    score_threshold: float | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[dict]
    trace_id: str


@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    session_id = None
    if req.session_id:
        try:
            sid = UUID(req.session_id)
            result = await db.execute(select(ChatSession).where(ChatSession.id == sid))
            if result.scalar_one_or_none():
                session_id = sid
        except ValueError:
            pass

    if not session_id:
        session = ChatSession(title=req.query[:80])
        db.add(session)
        await db.commit()
        session_id = session.id

    tracer = Tracer()

    evaluate = settings.ENABLE_ONLINE_EVAL if req.evaluate is None else req.evaluate

    retrieval_query = req.query
    if session_id:
        history_rows = (
            await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at)
            )
        ).scalars().all()
        history = [(m.role, m.content) for m in history_rows]
        if should_rewrite(req.query, history):
            async with tracer.span(
                "query_rewrite", attributes={"original": req.query}
            ) as span:
                retrieval_query = await rewrite_query(req.query, history)
                span.attributes["rewritten"] = retrieval_query

    chunks = await retrieve(
        query=retrieval_query,
        paper_ids=req.paper_ids,
        top_k=20,
        db=db,
        tracer=tracer,
        score_threshold=req.score_threshold,
    )
    chunks = await rerank(query=req.query, chunks=chunks, top_k=5, tracer=tracer)

    if req.stream:
        return StreamingResponse(
            _stream_and_store(req.query, chunks, session_id, tracer, evaluate),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    error_occurred = False
    try:
        result = await generate(query=req.query, chunks=chunks, tracer=tracer)
        answer_text = result.answer
        citations_data = [c.__dict__ for c in result.citations] if result.citations else None
    except Exception as e:
        error_occurred = True
        answer_text = f"An error occurred while generating response: {e}"
        citations_data = None

    scores = (
        await run_online_eval(req.query, answer_text, chunks, error_occurred=error_occurred, tracer=tracer)
        if evaluate
        else None
    )

    db.add(ChatMessage(session_id=session_id, role="user", content=req.query))
    db.add(
        ChatMessage(
            session_id=session_id,
            role="assistant",
            content=answer_text,
            citations=citations_data,
            eval_scores=scores,
            trace_id=tracer.trace_id,
        )
    )
    await tracer.store(db)
    await db.commit()

    return ChatResponse(
        session_id=str(session_id),
        answer=answer_text,
        citations=citations_data or [],
        trace_id=tracer.trace_id,
    )


async def _stream_and_store(
    query: str,
    chunks: list,
    session_id: UUID,
    tracer: Tracer,
    evaluate: bool,
):
    factory = _get_session_factory()
    async with factory() as db:
        db.add(ChatMessage(session_id=session_id, role="user", content=query))
        await db.commit()

    full_text = ""
    final_citations = None
    error_occurred = False

    try:
        async for event_str in stream_generate(
            query, chunks, session_id=str(session_id), tracer=tracer
        ):
            yield event_str

            lines = event_str.strip().split("\n")
            event_type = ""
            for line in lines:
                if line.startswith("event: "):
                    event_type = line[7:]
                    if event_type == "error":
                        error_occurred = True
                elif line.startswith("data: ") and event_type == "token":
                    payload = json.loads(line[6:])
                    full_text += payload.get("text", "")
                elif line.startswith("data: ") and event_type == "done":
                    payload = json.loads(line[6:])
                    final_citations = payload.get("citations")
    except Exception as e:
        error_occurred = True
        logger.exception("Error during SSE stream: %s", e)
    finally:
        content_to_save = full_text or "Sorry, an error occurred during response generation."
        scores = (
            await run_online_eval(query, content_to_save, chunks, error_occurred=error_occurred, tracer=tracer)
            if evaluate
            else None
        )
        async with factory() as db:
            db.add(
                ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=content_to_save,
                    citations=final_citations,
                    eval_scores=scores,
                    trace_id=tracer.trace_id,
                )
            )
            await tracer.store(db)
            await db.commit()


@router.get("/chat/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
):
    sessions = (
        await db.execute(
            select(ChatSession)
            .order_by(ChatSession.created_at.desc())
        )
    ).scalars().all()

    return [
        {
            "id": str(s.id),
            "title": s.title,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/chat/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    msgs = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
    ).scalars().all()

    return {
        "id": str(session.id),
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "trace_id": m.trace_id,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    session = (
        await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    ).scalar_one_or_none()

    if not session:
        return {"status": "deleted", "id": str(session_id)}

    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()
    return {"status": "deleted", "id": str(session_id)}

