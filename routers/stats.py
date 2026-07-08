import datetime
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from auth.dependencies import get_current_user
from database import get_async_db

router = APIRouter(prefix="/stats", tags=["stats"])


def _range_start(range_value: str) -> datetime.date:
    match = re.fullmatch(r"(\d+)d", range_value)
    if not match:
        raise HTTPException(status_code=400, detail="range must use Nd format, for example 30d")
    days = int(match.group(1))
    if days <= 0 or days > 365:
        raise HTTPException(status_code=400, detail="range must be between 1d and 365d")
    return datetime.date.today() - datetime.timedelta(days=days)


@router.get("/user/{user_id}", response_model=List[schemas.DailyUserStatsOut])
async def get_user_stats(
    user_id: int,
    range: str = Query("30d", pattern=r"^\d+d$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "manager"] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this resource")

    start_date = _range_start(range)
    result = await db.execute(
        select(models.DailyUserStats)
        .where(
            models.DailyUserStats.user_id == user_id,
            models.DailyUserStats.stat_date >= start_date,
        )
        .order_by(models.DailyUserStats.stat_date.desc(), models.DailyUserStats.event_type)
    )
    return result.scalars().all()


@router.get("/search", response_model=List[schemas.DailySearchStatsOut])
async def get_search_stats(
    range: str = Query("30d", pattern=r"^\d+d$"),
    keyword: str | None = Query(None, min_length=1, max_length=255),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="You do not have permission to access this resource")

    start_date = _range_start(range)
    statement = select(models.DailySearchStats).where(models.DailySearchStats.stat_date >= start_date)
    if keyword:
        normalized_keyword = " ".join(keyword.casefold().split())
        statement = statement.where(models.DailySearchStats.normalized_keyword == normalized_keyword)

    result = await db.execute(
        statement.order_by(models.DailySearchStats.stat_date.desc(), models.DailySearchStats.search_count.desc())
    )
    return result.scalars().all()
