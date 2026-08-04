from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_latency_percentiles(
    db: AsyncSession,
    step: str | None = None,
    hours: int = 24,
) -> list[dict]:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)

    params = {"cutoff": cutoff}
    step_filter = ""
    if step:
        step_filter = "AND name = :step"
        params["step"] = step

    rows = await db.execute(
        text(f"""
            SELECT
                name,
                percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) AS p50,
                percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95,
                percentile_cont(0.99) WITHIN GROUP (ORDER BY duration_ms) AS p99,
                COUNT(*) AS sample_count
            FROM trace_spans
            WHERE start_time > :cutoff {step_filter}
            GROUP BY name
            ORDER BY name
        """),
        params,
    )

    return [
        {
            "step": r.name,
            "p50_ms": round(r.p50, 1) if r.p50 is not None else 0,
            "p95_ms": round(r.p95, 1) if r.p95 is not None else 0,
            "p99_ms": round(r.p99, 1) if r.p99 is not None else 0,
            "sample_count": r.sample_count,
        }
        for r in rows
    ]


async def get_empty_result_rate(db: AsyncSession, hours: int = 24) -> tuple[float, int]:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)

    row = await db.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE attributes->>'empty_result' = 'true') AS empty_count,
                COUNT(*) AS total
            FROM trace_spans
            WHERE name = 'vector_search'
            AND start_time > :cutoff
        """),
        {"cutoff": cutoff},
    )
    r = row.one()
    if r.total == 0:
        return 0.0, 0
    return r.empty_count / r.total, r.total


async def get_health_score(db: AsyncSession) -> dict:
    latency_rows = await get_latency_percentiles(db, hours=24)

    targets = {
        "embed": 1000,
        "vector_search": 500,
        "rerank": 2000,
        "generate": 10000,
    }

    step_scores = []
    for row in latency_rows:
        target = targets.get(row["step"], 5000)
        p95 = row["p95_ms"]
        if p95 <= target:
            step_scores.append(100)
        else:
            step_scores.append(max(0, round(100 * (1 - (p95 - target) / target))))

    latency_score = round(sum(step_scores) / len(step_scores)) if step_scores else 0

    empty_rate, total_searches = await get_empty_result_rate(db, hours=24)
    empty_result_score = round(100 * (1 - empty_rate)) if total_searches > 0 else 0

    row = await db.execute(
        text("""
            SELECT AVG((eval_scores->>'citation_accuracy')::float) AS avg_accuracy
            FROM chat_messages
            WHERE eval_scores IS NOT NULL
            AND eval_scores->>'citation_accuracy' IS NOT NULL
        """),
    )
    r = row.one()
    citation_score = round((r.avg_accuracy or 0) * 100)

    if not latency_rows and total_searches == 0 and r.avg_accuracy is None:
        health_score = 0
    else:
        health_score = round(
            latency_score * 0.33 + empty_result_score * 0.33 + citation_score * 0.34
        )

    return {
        "health_score": health_score,
        "components": {
            "latency": {"score": latency_score, "weight": 0.33},
            "empty_result_rate": {"score": empty_result_score, "weight": 0.33},
            "citation_accuracy": {"score": citation_score, "weight": 0.34},
        },
        "details": {
            "latency_percentiles": latency_rows,
            "empty_result_rate_24h": round(empty_rate, 4),
            "avg_citation_accuracy": round(r.avg_accuracy or 0, 4),
        },
    }


async def get_timeseries(db: AsyncSession, range_days: int = 7) -> list[dict]:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=range_days)

    rows = await db.execute(
        text("""
            SELECT
                date_trunc('day', start_time) AS day,
                COUNT(*) AS total_spans,
                COUNT(*) FILTER (WHERE name = 'embed') AS embed_count,
                COUNT(*) FILTER (WHERE name = 'vector_search') AS search_count,
                COUNT(*) FILTER (WHERE name = 'rerank') AS rerank_count,
                COUNT(*) FILTER (WHERE name = 'generate') AS generate_count,
                AVG(duration_ms) FILTER (WHERE name = 'embed') AS avg_embed_ms,
                AVG(duration_ms) FILTER (WHERE name = 'vector_search') AS avg_search_ms,
                AVG(duration_ms) FILTER (WHERE name = 'rerank') AS avg_rerank_ms,
                AVG(duration_ms) FILTER (WHERE name = 'generate') AS avg_generate_ms,
                SUM((attributes->>'input_tokens')::int) FILTER (WHERE name = 'generate') AS input_tokens,
                SUM((attributes->>'output_tokens')::int) FILTER (WHERE name = 'generate') AS output_tokens,
                COUNT(*) FILTER (
                    WHERE name = 'vector_search'
                    AND attributes->>'empty_result' = 'true'
                ) AS empty_search_count
            FROM trace_spans
            WHERE start_time > :cutoff
            GROUP BY date_trunc('day', start_time)
            ORDER BY day
        """),
        {"cutoff": cutoff},
    )

    return [
        {
            "date": r.day.isoformat(),
            "span_counts": {
                "total": r.total_spans,
                "embed": r.embed_count,
                "search": r.search_count,
                "rerank": r.rerank_count,
                "generate": r.generate_count,
            },
            "avg_latency_ms": {
                "embed": round(r.avg_embed_ms, 1) if r.avg_embed_ms else 0,
                "search": round(r.avg_search_ms, 1) if r.avg_search_ms else 0,
                "rerank": round(r.avg_rerank_ms, 1) if r.avg_rerank_ms else 0,
                "generate": round(r.avg_generate_ms, 1) if r.avg_generate_ms else 0,
            },
            "token_usage": {
                "input": r.input_tokens or 0,
                "output": r.output_tokens or 0,
            },
            "empty_search_count": r.empty_search_count,
        }
        for r in rows
    ]


async def get_per_paper_stats(db: AsyncSession) -> list[dict]:
    rows = await db.execute(
        text("""
            SELECT
                c.item->>'paper_id' AS paper_id,
                COALESCE(p.title, 'Untitled Paper') AS title,
                COUNT(*) AS citation_count,
                AVG((cm.eval_scores->>'citation_accuracy')::float) AS avg_citation_accuracy
            FROM chat_messages cm
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE WHEN cm.citations IS NOT NULL AND jsonb_typeof(cm.citations) = 'array'
                     THEN cm.citations ELSE '[]'::jsonb END
            ) AS c(item)
            LEFT JOIN papers p ON p.id::text = c.item->>'paper_id'
            WHERE c.item->>'paper_id' IS NOT NULL
            GROUP BY c.item->>'paper_id', p.title
            ORDER BY citation_count DESC
        """),
    )

    return [
        {
            "paper_id": r.paper_id,
            "title": r.title,
            "citation_count": r.citation_count,
            "avg_citation_accuracy": round(r.avg_citation_accuracy, 4) if r.avg_citation_accuracy else 0,
        }
        for r in rows
    ]


async def get_low_scoring_queries(
    db: AsyncSession,
    limit: int = 20,
    threshold: float = 0.8,
) -> list[dict]:
    rows = await db.execute(
        text(r"""
            SELECT
                m.content AS query,
                m.created_at AS timestamp,
                COALESCE(
                    (follow.eval_scores->>'citation_accuracy')::float,
                    (
                        SELECT AVG((x.value)::float)
                        FROM jsonb_each_text(follow.eval_scores) AS x
                        WHERE x.value ~ '^[-+]?[0-9]*\.?[0-9]+$'
                    )
                ) AS score
            FROM chat_messages m
            CROSS JOIN LATERAL (
                SELECT cm.eval_scores
                FROM chat_messages cm
                WHERE cm.session_id = m.session_id
                  AND cm.role = 'assistant'
                  AND cm.created_at > m.created_at
                  AND cm.eval_scores IS NOT NULL
                ORDER BY cm.created_at ASC
                LIMIT 1
            ) AS follow
            WHERE m.role = 'user'
        """),
    )

    low = []
    for r in rows:
        if r.score is None or r.score >= threshold:
            continue
        low.append(
            {
                "query": r.query,
                "score": round(r.score, 4),
                "timestamp": r.timestamp.isoformat(),
            }
        )

    low.sort(key=lambda x: x["timestamp"], reverse=True)
    return low[:limit]


async def get_traces_list(
    db: AsyncSession,
    search: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    stmt = text("""
        SELECT
            t.trace_id,
            MIN(t.start_time) AS created_at,
            SUM(t.duration_ms) AS total_duration_ms,
            COUNT(t.id) AS span_count,
            BOOL_OR(t.attributes->>'finish_reason' = 'error') AS has_error,
            BOOL_OR((t.attributes->>'fallback')::boolean = true) AS has_fallback,
            MAX(cm.content) FILTER (WHERE cm.role = 'user') AS query
        FROM trace_spans t
        LEFT JOIN chat_messages cm ON cm.trace_id = t.trace_id
        GROUP BY t.trace_id
        ORDER BY MIN(t.start_time) DESC
    """)
    rows = (await db.execute(stmt)).fetchall()

    traces = []
    for r in rows:
        trace_id = str(r.trace_id)
        created_at = r.created_at.isoformat() if r.created_at else ""
        query = r.query or f"Trace {trace_id[:8]}"
        has_error = bool(r.has_error)
        has_fallback = bool(r.has_fallback)
        total_duration = int(r.total_duration_ms or 0)

        # Status filter
        if status == "error" and not has_error:
            continue
        if status == "fallback" and not has_fallback:
            continue
        if status == "slow" and total_duration < 2500:
            continue

        # Search filter
        if search:
            s = search.lower()
            if s not in trace_id.lower() and s not in query.lower():
                continue

        traces.append({
            "trace_id": trace_id,
            "created_at": created_at,
            "total_duration_ms": total_duration,
            "span_count": r.span_count,
            "has_error": has_error,
            "has_fallback": has_fallback,
            "query": query,
        })

    paginated = traces[offset: offset + limit]
    return {
        "items": paginated,
        "total": len(traces),
        "page": (offset // limit) + 1,
        "page_size": limit,
    }


async def get_trace_details(db: AsyncSession, trace_id: str) -> dict | None:
    rows = (await db.execute(
        text("""
            SELECT id, trace_id, span_id, parent_span_id, name, attributes, start_time, end_time, duration_ms
            FROM trace_spans
            WHERE trace_id = :trace_id
            ORDER BY start_time ASC
        """),
        {"trace_id": trace_id},
    )).fetchall()

    if not rows:
        return None

    spans = []
    first_time = rows[0].start_time
    total_duration = sum(r.duration_ms or 0 for r in rows)

    for r in rows:
        offset_ms = int((r.start_time - first_time).total_seconds() * 1000) if r.start_time and first_time else 0
        spans.append({
            "id": str(r.id),
            "trace_id": str(r.trace_id),
            "span_id": r.span_id,
            "parent_span_id": r.parent_span_id,
            "name": r.name,
            "attributes": r.attributes or {},
            "start_time": r.start_time.isoformat() if r.start_time else "",
            "end_time": r.end_time.isoformat() if r.end_time else "",
            "offset_ms": offset_ms,
            "duration_ms": r.duration_ms or 0,
        })

    return {
        "trace_id": trace_id,
        "created_at": rows[0].start_time.isoformat() if rows[0].start_time else "",
        "total_duration_ms": total_duration,
        "spans": spans,
    }


async def get_surfaced_traces(db: AsyncSession, limit: int = 10) -> dict:
    rows = (await db.execute(
        text("""
            SELECT
                t.trace_id,
                MIN(t.start_time) AS created_at,
                SUM(t.duration_ms) AS total_duration_ms,
                BOOL_OR(t.attributes->>'finish_reason' = 'error') AS has_error,
                BOOL_OR((t.attributes->>'fallback')::boolean = true) AS has_fallback
            FROM trace_spans t
            GROUP BY t.trace_id
            ORDER BY MIN(t.start_time) DESC
        """),
    )).fetchall()

    recent_errors = []
    slow_traces = []

    for r in rows:
        item = {
            "trace_id": str(r.trace_id),
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "total_duration_ms": int(r.total_duration_ms or 0),
            "has_error": bool(r.has_error),
            "has_fallback": bool(r.has_fallback),
        }
        if (r.has_error or r.has_fallback) and len(recent_errors) < limit:
            recent_errors.append(item)
        if int(r.total_duration_ms or 0) >= 2000 and len(slow_traces) < limit:
            slow_traces.append(item)

    return {
        "recent_errors": recent_errors,
        "slow_traces": slow_traces,
    }


async def get_reranker_stats(db: AsyncSession, days: int = 7) -> dict:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    rows = (await db.execute(
        text("""
            SELECT
                DATE_TRUNC('day', start_time) AS day,
                COUNT(*) AS total_calls,
                COUNT(*) FILTER (WHERE (attributes->>'fallback')::boolean = true) AS fallback_calls
            FROM trace_spans
            WHERE name = 'rerank'
              AND start_time > :cutoff
            GROUP BY 1
            ORDER BY 1 ASC
        """),
        {"cutoff": cutoff},
    )).fetchall()

    daily = []
    total_calls = 0
    total_fallbacks = 0

    for r in rows:
        tc = r.total_calls
        fc = r.fallback_calls
        total_calls += tc
        total_fallbacks += fc
        rate = round((fc / tc) * 100, 2) if tc > 0 else 0.0
        daily.append({
            "date": r.day.strftime("%Y-%m-%d"),
            "total_calls": tc,
            "fallback_calls": fc,
            "fallback_rate_pct": rate,
        })

    overall_rate = round((total_fallbacks / total_calls) * 100, 2) if total_calls > 0 else 0.0
    return {
        "total_calls": total_calls,
        "total_fallbacks": total_fallbacks,
        "fallback_rate_pct": overall_rate,
        "daily": daily,
    }


async def get_token_usage_stats(db: AsyncSession, days: int = 7) -> dict:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    rows = (await db.execute(
        text("""
            SELECT
                DATE_TRUNC('day', start_time) AS day,
                SUM(COALESCE((attributes->>'input_tokens')::int, 0)) AS total_input_tokens,
                SUM(COALESCE((attributes->>'output_tokens')::int, 0)) AS total_output_tokens
            FROM trace_spans
            WHERE name = 'generate'
              AND start_time > :cutoff
            GROUP BY 1
            ORDER BY 1 ASC
        """),
        {"cutoff": cutoff},
    )).fetchall()

    daily = []
    grand_input = 0
    grand_output = 0

    for r in rows:
        inp = int(r.total_input_tokens or 0)
        outp = int(r.total_output_tokens or 0)
        grand_input += inp
        grand_output += outp
        daily.append({
            "date": r.day.strftime("%Y-%m-%d"),
            "input_tokens": inp,
            "output_tokens": outp,
            "total_tokens": inp + outp,
        })

    return {
        "total_input_tokens": grand_input,
        "total_output_tokens": grand_output,
        "total_tokens": grand_input + grand_output,
        "daily": daily,
    }
