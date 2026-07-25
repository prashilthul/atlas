from datetime import datetime
from typing import Optional
from uuid import uuid4

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    authors: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="processing")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class PaperSection(Base):
    __tablename__ = "paper_sections"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    paper_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    heading: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    paper_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paper_sections.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(768), nullable=False)
    meta_data: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    paper_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    cited_title: Mapped[str] = mapped_column(String, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    marker: Mapped[str] = mapped_column(String, nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    eval_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class TraceSpan(Base):
    __tablename__ = "trace_spans"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    trace_id: Mapped[str] = mapped_column(String, nullable=False)
    span_id: Mapped[str] = mapped_column(String, nullable=False)
    parent_span_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
