import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.database import get_db
from app.models import ChatMessage, ChatSession
from app.services.generator import generate, stream_generate
from app.services.online_eval import run_online_eval
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
    if req.session_id:
        try:
            sid = UUID(req.session_id)
        except ValueError:
            raise HTTPException(400, "Invalid session ID")
        result = await db.execute(select(ChatSession).where(ChatSession.id == sid))
        if not result.scalar_one_or_none():
            raise HTTPException(404, "Session not found")
        session_id = sid
    else:
        session = ChatSession(title=req.query[:80])
        db.add(session)
        await db.flush()
        session_id = session.id

    tracer = Tracer()

    evaluate = settings.ENABLE_ONLINE_EVAL if req.evaluate is None else req.evaluate

    chunks = await retrieve(query=req.query, paper_ids=req.paper_ids, top_k=20, db=db, tracer=tracer)
    chunks = await rerank(query=req.query, chunks=chunks, top_k=5, tracer=tracer)

    if req.stream:
        return EventSourceResponse(
            _stream_and_store(req.query, chunks, session_id, db, tracer, evaluate)
        )

    result = await generate(query=req.query, chunks=chunks, tracer=tracer)
    scores = await run_online_eval(req.query, result.answer, chunks, tracer=tracer) if evaluate else None

    db.add(ChatMessage(session_id=session_id, role="user", content=req.query))
    db.add(
        ChatMessage(
            session_id=session_id,
            role="assistant",
            content=result.answer,
            citations=[c.__dict__ for c in result.citations] if result.citations else None,
            eval_scores=scores,
        )
    )
    await tracer.store(db)
    await db.commit()

    return ChatResponse(
        session_id=str(session_id),
        answer=result.answer,
        citations=[c.__dict__ for c in result.citations],
        trace_id=tracer.trace_id,
    )


async def _stream_and_store(
    query: str,
    chunks: list,
    session_id: UUID,
    db: AsyncSession,
    tracer: Tracer,
    evaluate: bool,
):
    db.add(ChatMessage(session_id=session_id, role="user", content=query))
    await db.flush()

    full_text = ""
    final_citations = None

    async for event_str in stream_generate(query, chunks, tracer=tracer):
        yield event_str

        lines = event_str.strip().split("\n")
        event_type = ""
        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: ") and event_type == "token":
                payload = json.loads(line[6:])
                full_text += payload.get("text", "")
            elif line.startswith("data: ") and event_type == "done":
                payload = json.loads(line[6:])
                final_citations = payload.get("citations")

    if full_text:
        scores = await run_online_eval(query, full_text, chunks, tracer=tracer) if evaluate else None
        db.add(
            ChatMessage(
                session_id=session_id,
                role="assistant",
                content=full_text,
                citations=final_citations,
                eval_scores=scores,
            )
        )
    await tracer.store(db)
    await db.commit()


@router.get("/sessions/{session_id}")
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
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }
