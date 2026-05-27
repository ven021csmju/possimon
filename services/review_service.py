import datetime
import math
from typing import Dict, List

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from models.review import ReviewCreate


def to_object_id(value: str, field_name: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        )
    return ObjectId(value)


def serialize_review(review: Dict) -> Dict:
    return {
        "id": str(review["_id"]),
        "product_id": str(review["product_id"]),
        "user_id": str(review["user_id"]),
        "username": review["username"],
        "rating": review["rating"],
        "comment": review["comment"],
        "images": review.get("images", []),
        "created_at": review["created_at"],
    }


async def get_product_rating_summary(db: AsyncIOMotorDatabase, product_id: ObjectId) -> Dict:
    pipeline = [
        {"$match": {"product_id": product_id}},
        {
            "$group": {
                "_id": "$product_id",
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


async def sync_product_review_stats(db: AsyncIOMotorDatabase, product_id: ObjectId) -> Dict:
    summary = await get_product_rating_summary(db, product_id)
    await db.products.update_one(
        {"_id": product_id},
        {
            "$set": {
                "average_rating": summary["average_rating"],
                "review_count": summary["review_count"],
                "updated_at": datetime.datetime.utcnow(),
            }
        },
    )
    return summary


async def create_review(db: AsyncIOMotorDatabase, review: ReviewCreate) -> Dict:
    product_id = to_object_id(review.product_id, "product_id")
    user_id = to_object_id(review.user_id, "user_id")

    product = await db.products.find_one({"_id": product_id})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    await db.users.update_one(
        {"_id": user_id},
        {
            "$set": {
                "username": review.username,
                "updated_at": datetime.datetime.utcnow(),
            },
            "$setOnInsert": {"created_at": datetime.datetime.utcnow()},
        },
        upsert=True,
    )

    review_doc = {
        "product_id": product_id,
        "user_id": user_id,
        "username": review.username,
        "rating": review.rating,
        "comment": review.comment,
        "images": review.images,
        "created_at": datetime.datetime.utcnow(),
    }

    try:
        result = await db.reviews.insert_one(review_doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already reviewed this product",
        )

    await sync_product_review_stats(db, product_id)
    created_review = await db.reviews.find_one({"_id": result.inserted_id})
    return serialize_review(created_review)


async def get_reviews_by_product(
    db: AsyncIOMotorDatabase,
    product_id: str,
    page: int,
    limit: int,
) -> Dict:
    product_object_id = to_object_id(product_id, "product_id")

    product = await db.products.find_one({"_id": product_object_id})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    skip = (page - 1) * limit
    cursor = (
        db.reviews.find({"product_id": product_object_id})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    reviews: List[Dict] = [serialize_review(review) async for review in cursor]
    summary = await get_product_rating_summary(db, product_object_id)
    total_pages = math.ceil(summary["review_count"] / limit) if summary["review_count"] else 0

    return {
        "product_id": product_id,
        "average_rating": summary["average_rating"],
        "review_count": summary["review_count"],
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "reviews": reviews,
    }
