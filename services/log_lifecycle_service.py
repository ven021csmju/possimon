import asyncio
import datetime
import gzip
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

import models
from core.config import settings
from database import AsyncSessionLocal
from database_nosql import get_mongo_db

logger = logging.getLogger(__name__)
LOG_LIFECYCLE_LOCK_ID = 834260817


def _json_default(value: Any):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _day_bounds(day: datetime.date) -> tuple[datetime.datetime, datetime.datetime]:
    start = datetime.datetime.combine(day, datetime.time.min)
    end = start + datetime.timedelta(days=1)
    return start, end


def _normalize_keyword(keyword: str) -> str:
    return " ".join(keyword.casefold().split())


def _archive_path(collection_name: str, day: datetime.date) -> Path:
    return (
        Path(settings.LOG_ARCHIVE_DIR)
        / collection_name
        / f"year={day.year:04d}"
        / f"month={day.month:02d}"
        / f"{collection_name}_{day.isoformat()}.json.gz"
    )


def _write_json_gz(path: Path, documents: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as file:
        for document in documents:
            file.write(json.dumps(document, default=_json_default, ensure_ascii=False))
            file.write("\n")


async def create_user_log(db: AsyncIOMotorDatabase, log: Dict[str, Any]) -> str:
    if not log.get("timestamp"):
        log["timestamp"] = _utcnow()
    log.setdefault("lifecycle", {})
    result = await db.user_logs.insert_one(log)
    return str(result.inserted_id)


async def create_search_log(db: AsyncIOMotorDatabase, log: Dict[str, Any]) -> str:
    if not log.get("timestamp"):
        log["timestamp"] = _utcnow()
    if not log.get("normalized_keyword"):
        log["normalized_keyword"] = _normalize_keyword(log["keyword"])
    log.setdefault("lifecycle", {})
    result = await db.search_logs.insert_one(log)
    return str(result.inserted_id)


async def _days_ready_for_summary(
    mongo_db: AsyncIOMotorDatabase,
    collection_name: str,
    cutoff: datetime.datetime,
) -> List[datetime.date]:
    pipeline = [
        {
            "$match": {
                "timestamp": {"$lt": cutoff},
                "lifecycle.summarized_at": {"$exists": False},
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$timestamp",
                    }
                }
            }
        },
        {"$sort": {"_id": 1}},
    ]
    days = []
    async for row in mongo_db[collection_name].aggregate(pipeline):
        days.append(datetime.date.fromisoformat(row["_id"]))
    return days


async def _archive_collection_day(
    mongo_db: AsyncIOMotorDatabase,
    collection_name: str,
    day: datetime.date,
) -> str | None:
    start, end = _day_bounds(day)
    query = {
        "timestamp": {"$gte": start, "$lt": end},
        "lifecycle.summarized_at": {"$exists": False},
    }
    documents = [document async for document in mongo_db[collection_name].find(query)]
    if not documents:
        return None

    path = _archive_path(collection_name, day)
    await asyncio.to_thread(_write_json_gz, path, documents)
    return str(path)


async def _aggregate_user_stats(
    mongo_db: AsyncIOMotorDatabase,
    day: datetime.date,
) -> List[Dict[str, Any]]:
    start, end = _day_bounds(day)
    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": start, "$lt": end},
                "lifecycle.summarized_at": {"$exists": False},
            }
        },
        {
            "$group": {
                "_id": {
                    "user_id": "$user_id",
                    "event_type": "$event_type",
                    "product_id": {"$ifNull": ["$product_id", 0]},
                },
                "event_count": {"$sum": 1},
            }
        },
    ]
    rows = []
    async for row in mongo_db.user_logs.aggregate(pipeline):
        key = row["_id"]
        if key.get("user_id") is None:
            continue
        rows.append(
            {
                "stat_date": day,
                "user_id": int(key["user_id"]),
                "event_type": str(key["event_type"]),
                "product_id": int(key.get("product_id") or 0),
                "event_count": int(row["event_count"]),
            }
        )
    return rows


async def _aggregate_search_stats(
    mongo_db: AsyncIOMotorDatabase,
    day: datetime.date,
) -> List[Dict[str, Any]]:
    start, end = _day_bounds(day)
    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": start, "$lt": end},
                "lifecycle.summarized_at": {"$exists": False},
            }
        },
        {
            "$group": {
                "_id": {
                    "normalized_keyword": {
                        "$trim": {
                            "input": {
                                "$toLower": {"$ifNull": ["$normalized_keyword", "$keyword"]}
                            }
                        }
                    },
                    "user_id": "$user_id",
                },
                "keyword": {"$first": "$keyword"},
                "search_count": {"$sum": 1},
                "total_results": {"$sum": {"$ifNull": ["$result_count", 0]}},
            }
        },
    ]
    rows = []
    async for row in mongo_db.search_logs.aggregate(pipeline):
        key = row["_id"]
        if not key.get("normalized_keyword"):
            continue
        keyword = row.get("keyword") or key["normalized_keyword"]
        normalized_keyword = _normalize_keyword(key["normalized_keyword"])
        search_count = int(row["search_count"])
        total_results = int(row["total_results"])
        rows.append(
            {
                "stat_date": day,
                "keyword": keyword,
                "normalized_keyword": normalized_keyword,
                "user_id": int(key.get("user_id") or 0),
                "search_count": search_count,
                "total_results": total_results,
                "avg_results": total_results / search_count if search_count else 0.0,
            }
        )
    return rows


def _insert_for_session(db: AsyncSession, table):
    dialect_name = db.bind.dialect.name if db.bind is not None else "postgresql"
    if dialect_name == "sqlite":
        return sqlite_insert(table)
    return postgres_insert(table)


async def _upsert_user_stats(db: AsyncSession, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    table = models.DailyUserStats.__table__
    statement = _insert_for_session(db, table).values(rows)
    set_values = {
        "event_count": statement.excluded.event_count,
        "updated_at": _utcnow(),
    }
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        statement = statement.on_conflict_do_update(
            index_elements=["stat_date", "user_id", "event_type", "product_id"],
            set_=set_values,
        )
    else:
        statement = statement.on_conflict_do_update(
            constraint="uq_daily_user_stats_key",
            set_=set_values,
        )
    await db.execute(statement)


async def _upsert_search_stats(db: AsyncSession, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    table = models.DailySearchStats.__table__
    statement = _insert_for_session(db, table).values(rows)
    set_values = {
        "keyword": statement.excluded.keyword,
        "search_count": statement.excluded.search_count,
        "total_results": statement.excluded.total_results,
        "avg_results": statement.excluded.avg_results,
        "updated_at": _utcnow(),
    }
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        statement = statement.on_conflict_do_update(
            index_elements=["stat_date", "normalized_keyword", "user_id"],
            set_=set_values,
        )
    else:
        statement = statement.on_conflict_do_update(
            constraint="uq_daily_search_stats_key",
            set_=set_values,
        )
    await db.execute(statement)


async def _mark_collection_day_summarized(
    mongo_db: AsyncIOMotorDatabase,
    collection_name: str,
    day: datetime.date,
    archive_path: str | None,
    summarized_at: datetime.datetime,
) -> None:
    start, end = _day_bounds(day)
    await mongo_db[collection_name].update_many(
        {
            "timestamp": {"$gte": start, "$lt": end},
            "lifecycle.summarized_at": {"$exists": False},
        },
        {
            "$set": {
                "lifecycle.summarized_at": summarized_at,
                "lifecycle.archived_at": summarized_at,
                "lifecycle.archive_path": archive_path,
            }
        },
    )


async def _try_advisory_lock(db: AsyncSession) -> bool:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return True
    result = await db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": LOG_LIFECYCLE_LOCK_ID})
    return bool(result.scalar())


async def summarize_and_archive_logs() -> Dict[str, Any]:
    mongo_db = get_mongo_db()
    async with AsyncSessionLocal() as lock_db:
        if not await _try_advisory_lock(lock_db):
            return {"skipped": True, "reason": "log lifecycle job is already running"}

        cutoff = _utcnow() - datetime.timedelta(days=settings.LOG_SUMMARY_AFTER_DAYS)
        user_days = await _days_ready_for_summary(mongo_db, "user_logs", cutoff)
        search_days = await _days_ready_for_summary(mongo_db, "search_logs", cutoff)
        days = sorted(set(user_days + search_days))
        result = {"days": len(days), "user_stats_rows": 0, "search_stats_rows": 0}

        for day in days:
            user_archive_path = await _archive_collection_day(mongo_db, "user_logs", day)
            search_archive_path = await _archive_collection_day(mongo_db, "search_logs", day)
            user_rows = await _aggregate_user_stats(mongo_db, day)
            search_rows = await _aggregate_search_stats(mongo_db, day)

            async with AsyncSessionLocal() as db:
                async with db.begin():
                    await _upsert_user_stats(db, user_rows)
                    await _upsert_search_stats(db, search_rows)

            summarized_at = _utcnow()
            await _mark_collection_day_summarized(mongo_db, "user_logs", day, user_archive_path, summarized_at)
            await _mark_collection_day_summarized(mongo_db, "search_logs", day, search_archive_path, summarized_at)
            result["user_stats_rows"] += len(user_rows)
            result["search_stats_rows"] += len(search_rows)

        return result


async def run_log_lifecycle_job() -> None:
    try:
        await summarize_and_archive_logs()
    except HTTPException as exc:
        logger.warning("Skipping log lifecycle job: %s", exc.detail)
    except Exception:
        logger.exception("Log lifecycle job failed")
