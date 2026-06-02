import datetime
import math
import uuid
import io
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException, status, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from models.review import ReviewCreate
from core.config import settings
from services.storage_service import StorageService


async def resolve_user_id(db: AsyncIOMotorDatabase, user_id: str, username: str) -> Any:
    now = datetime.datetime.utcnow()
    if ObjectId.is_valid(user_id):
        object_id = ObjectId(user_id)
        await db.users.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "username": username,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        return str(object_id)

    await db.users.update_one(
        {"external_id": user_id},
        {
            "$set": {
                "username": username,
                "user_id": user_id,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    return user_id


def serialize_review(review: Dict) -> Dict:
    return {
        "id": str(review["_id"]),
        "wine_id": review["wine_id"],
        "user_id": str(review["user_id"]),
        "username": review["username"],
        "rating": review["rating"],
        "comment": review["comment"],
        "images": review.get("images", []),
        "videos": review.get("videos", []),
        "created_at": review["created_at"],
    }


async def get_rating_summary(db: AsyncIOMotorDatabase, wine_id: int) -> Dict:
    pipeline = [
        {"$match": {"wine_id": wine_id}},
        {
            "$group": {
                "_id": "$wine_id",
                "average_rating": {"$avg": "$rating"},
                "review_count": {"$sum": 1},
            }
        },
    ]
    result = await db.reviews.aggregate(pipeline).to_list(length=1)
    if not result:
        return {"average_rating": 0.0, "review_count": 0}

    return {
        "average_rating": round(result[0]["average_rating"], 2),
        "review_count": result[0]["review_count"],
    }


async def get_bulk_rating_summaries(db: AsyncIOMotorDatabase, wine_ids: List[int]) -> Dict[int, Dict]:
    if not wine_ids:
        return {}
        
    pipeline = [
        {"$match": {"wine_id": {"$in": wine_ids}}},
        {
            "$group": {
                "_id": "$wine_id",
                "average_rating": {"$avg": "$rating"},
                "review_count": {"$sum": 1},
            }
        },
    ]
    cursor = db.reviews.aggregate(pipeline)
    summaries = {}
    async for doc in cursor:
        summaries[doc["_id"]] = {
            "average_rating": round(doc["average_rating"], 2),
            "review_count": doc["review_count"],
        }
    
    # Fill in defaults for missing IDs
    for wid in wine_ids:
        if wid not in summaries:
            summaries[wid] = {"average_rating": 0.0, "review_count": 0}
            
    return summaries


async def create_review(db: AsyncIOMotorDatabase, review: ReviewCreate) -> Dict:
    user_id = await resolve_user_id(db, review.user_id, review.username)

    review_doc = {
        "wine_id": review.wine_id,
        "user_id": user_id,
        "username": review.username,
        "rating": review.rating,
        "comment": review.comment,
        "images": review.images,
        "videos": review.videos,
        "created_at": datetime.datetime.utcnow(),
    }

    try:
        result = await db.reviews.insert_one(review_doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already reviewed this wine",
        )

    created_review = await db.reviews.find_one({"_id": result.inserted_id})
    return serialize_review(created_review)


async def upload_review_media(file: UploadFile, is_video: bool = False):
    if is_video:
        return await StorageService.upload_video(file)
    return await StorageService.upload_image(file)


async def get_reviews_by_wine(
    db: AsyncIOMotorDatabase,
    wine_id: int,
    page: int,
    limit: int,
) -> Dict:
    skip = (page - 1) * limit
    match_query = {"wine_id": wine_id}
    
    cursor = (
        db.reviews.find(match_query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    reviews: List[Dict] = [serialize_review(review) async for review in cursor]
    summary = await get_rating_summary(db, wine_id)
    total_pages = math.ceil(summary["review_count"] / limit) if summary["review_count"] else 0

    return {
        "wine_id": wine_id,
        "average_rating": summary["average_rating"],
        "review_count": summary["review_count"],
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "reviews": reviews,
    }
