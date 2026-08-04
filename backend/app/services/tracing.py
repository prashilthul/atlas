import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    attributes: dict
    start_time: float  # unix ns
    end_time: float | None = None
    duration_ms: int | None = None


class Tracer:
    def __init__(self, trace_id: str | None = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.spans: list[Span] = []

    @asynccontextmanager
    async def span(self, name: str, attributes: dict | None = None, parent_span_id: str | None = None):
        span_id = str(uuid.uuid4())[:16]
        span = Span(
            trace_id=self.trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            attributes=attributes or {},
            start_time=time.time_ns(),
        )
        self.spans.append(span)
        try:
            yield span
        finally:
            span.end_time = time.time_ns()
            span.duration_ms = (span.end_time - span.start_time) // 1_000_000

    async def store(self, db):
        from app.models import TraceSpan

        for s in self.spans:
            db.add(TraceSpan(
                trace_id=s.trace_id,
                span_id=s.span_id,
                parent_span_id=s.parent_span_id,
                name=s.name,
                attributes=s.attributes,
                start_time=datetime.fromtimestamp(s.start_time / 1_000_000_000, tz=UTC).replace(tzinfo=None),
                end_time=datetime.fromtimestamp(s.end_time / 1_000_000_000, tz=UTC).replace(tzinfo=None) if s.end_time else None,
                duration_ms=s.duration_ms,
            ))
        await db.flush()

    def get_trace_spans_summary(self) -> list[dict]:
        summary = []
        for s in self.spans:
            is_error = s.attributes and (s.attributes.get("finish_reason") == "error" or s.attributes.get("fallback") is True)
            status = "error" if is_error else "ok"
            summary.append({
                "span_id": s.span_id,
                "name": s.name,
                "start_time_ns": s.start_time,
                "duration_ms": s.duration_ms or 0,
                "status": status,
                "attributes": s.attributes or {},
            })
        return summary
