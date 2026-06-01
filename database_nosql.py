import os
import logging
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(override=True)

logger = logging.getLogger(__name__)

MONGODB_URL = os.getenv("MONGODB_URL")

db = None
client = None

if MONGODB_URL:
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client["bottleclub"]
else:
    logger.warning("MONGODB_URL environment variable is not set. NoSQL features will be disabled.")

def get_mongo_db():
    if db is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503, 
            detail="MongoDB is not configured. This feature is unavailable."
        )
    return db


def _normalize_positive_int(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


async def migrate_review_collection() -> Dict[str, Any]:
    if db is None:
        logger.warning("Skipping MongoDB review migration: No database connection.")
        return {"skipped": True}

    reviews = db.reviews
    scanned = 0
    updated = 0
    removed_invalid = 0
    duplicate_groups = 0
    removed_duplicates = 0
    pairs: Dict[Tuple[int, str], List[Dict[str, Any]]] = {}

    async for review in reviews.find({}):
        scanned += 1
        set_fields: Dict[str, Any] = {}
        unset_fields: Dict[str, str] = {}

        wine_id = _normalize_positive_int(review.get("wine_id"))
        product_id = _normalize_positive_int(review.get("product_id"))
        if wine_id is None and product_id is not None:
            wine_id = product_id
            set_fields["wine_id"] = wine_id

        if "product_id" in review:
            unset_fields["product_id"] = ""

        raw_user_id = review.get("user_id")
        user_id = str(raw_user_id).strip() if raw_user_id is not None else ""
        if user_id and raw_user_id != user_id:
            set_fields["user_id"] = user_id

        if wine_id is None or not user_id:
            await reviews.delete_one({"_id": review["_id"]})
            removed_invalid += 1
            continue

        update_doc: Dict[str, Any] = {}
        if set_fields:
            update_doc["$set"] = set_fields
        if unset_fields:
            update_doc["$unset"] = unset_fields
        if update_doc:
            await reviews.update_one({"_id": review["_id"]}, update_doc)
            updated += 1

        review["wine_id"] = wine_id
        review["user_id"] = user_id
        pairs.setdefault((wine_id, user_id), []).append(review)

    for pair_reviews in pairs.values():
        if len(pair_reviews) <= 1:
            continue

        duplicate_groups += 1
        pair_reviews.sort(
            key=lambda item: (
                item.get("created_at") is not None,
                str(item.get("created_at")),
                str(item["_id"]),
            ),
            reverse=True,
        )
        duplicate_ids = [item["_id"] for item in pair_reviews[1:]]
        result = await reviews.delete_many({"_id": {"$in": duplicate_ids}})
        removed_duplicates += result.deleted_count

    result = {
        "scanned": scanned,
        "updated": updated,
        "removed_invalid": removed_invalid,
        "duplicate_groups": duplicate_groups,
        "removed_duplicates": removed_duplicates,
    }
    logger.info("MongoDB review migration completed: %s", result)
    return result


async def create_mongo_indexes():
    if db is None:
        logger.warning("Skipping MongoDB index creation: No database connection.")
        return

    await migrate_review_collection()

    await db.reviews.create_index(
        [("wine_id", 1), ("user_id", 1)],
        unique=True,
        name="uniq_review_wine_user",
    )
    await db.reviews.create_index(
        [("wine_id", 1), ("created_at", -1)],
        name="idx_reviews_wine_created_at",
    )
    await db.reviews.create_index([("user_id", 1)], name="idx_reviews_user")
    await db.users.create_index([("external_id", 1)], unique=True, sparse=True, name="uniq_users_external_id")
