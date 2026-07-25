from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_latency_percentiles(
    db: AsyncSession,
    step: str | None = None,
    hours: int = 24,
) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

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


async def get_empty_result_rate(db: AsyncSession, hours: int = 24) -> float:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

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
        return 0.0
    return r.empty_count / r.total


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

    latency_score = round(sum(step_scores) / len(step_scores)) if step_scores else 100

    empty_rate = await get_empty_result_rate(db, hours=24)
    empty_result_score = round(100 * (1 - empty_rate))

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
    cutoff = datetime.now(timezone.utc) - timedelta(days=range_days)

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
                p.title,
                COUNT(*) AS citation_count,
                AVG((cm.eval_scores->>'citation_accuracy')::float) AS avg_citation_accuracy
            FROM chat_messages cm
            CROSS JOIN LATERAL jsonb_array_elements(cm.citations) AS c(item)
            LEFT JOIN papers p ON p.id::text = c.item->>'paper_id'
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
