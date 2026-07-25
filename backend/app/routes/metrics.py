import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.metrics import (
    get_health_score,
    get_per_paper_stats,
    get_timeseries,
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _parse_range(range_str: str) -> int:
    match = re.match(r"^(\d+)([dh])$", range_str.strip())
    if not match:
        return 7
    value = int(match.group(1))
    unit = match.group(2)
    if unit == "h":
        return max(1, value // 24)
    return max(1, value)


@router.get("/summary")
async def metrics_summary(
    db: AsyncSession = Depends(get_db),
):
    health = await get_health_score(db)
    per_paper = await get_per_paper_stats(db)
    return {**health, "per_paper": per_paper}


@router.get("/timeseries")
async def metrics_timeseries(
    range: str = Query("7d", description="Range: Nd (days) or Nh (hours)"),
    db: AsyncSession = Depends(get_db),
):
    days = _parse_range(range)
    data = await get_timeseries(db, range_days=days)
    return {"range_days": days, "data": data}
