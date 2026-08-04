import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.metrics import (
    get_health_score,
    get_low_scoring_queries,
    get_per_paper_stats,
    get_reranker_stats,
    get_surfaced_traces,
    get_timeseries,
    get_token_usage_stats,
    get_trace_details,
    get_traces_list,
)

router = APIRouter(prefix="/api", tags=["metrics_and_traces"])


def _parse_range(range_str: str) -> int:
    match = re.match(r"^(\d+)([dh])$", range_str.strip())
    if not match:
        return 7
    value = int(match.group(1))
    unit = match.group(2)
    if unit == "h":
        return max(1, value // 24)
    return max(1, value)


@router.get("/metrics/summary")
async def metrics_summary(
    db: AsyncSession = Depends(get_db),
):
    health = await get_health_score(db)
    per_paper = await get_per_paper_stats(db)
    return {**health, "per_paper": per_paper}


@router.get("/metrics/timeseries")
async def metrics_timeseries(
    range: str = Query("7d", description="Range: Nd (days) or Nh (hours)"),
    db: AsyncSession = Depends(get_db),
):
    days = _parse_range(range)
    data = await get_timeseries(db, range_days=days)
    return {"range_days": days, "data": data}


@router.get("/metrics/low-scoring-queries")
async def metrics_low_scoring_queries(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await get_low_scoring_queries(db, limit=limit)


@router.get("/metrics/surfaced-traces")
async def surfaced_traces(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    return await get_surfaced_traces(db, limit=limit)


@router.get("/metrics/reranker-stats")
async def reranker_stats(
    range: str = Query("7d"),
    db: AsyncSession = Depends(get_db),
):
    days = _parse_range(range)
    return await get_reranker_stats(db, days=days)


@router.get("/metrics/token-usage")
async def token_usage_stats(
    range: str = Query("7d"),
    db: AsyncSession = Depends(get_db),
):
    days = _parse_range(range)
    return await get_token_usage_stats(db, days=days)


@router.get("/traces")
async def list_traces(
    search: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await get_traces_list(db, search=search, status=status, limit=limit, offset=offset)


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
):
    res = await get_trace_details(db, trace_id=trace_id)
    if not res:
        raise HTTPException(status_code=404, detail="Trace not found")
    return res
