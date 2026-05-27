import datetime
import math
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from models.review import ReviewCreate


PRODUCT_EXTERNAL_ID_FIELDS = ("product_id", "sku", "code", "external_id")
USER_EXTERNAL_ID_FIELDS = ("user_id", "username", "external_id")


def to_object_id(value: str, field_name: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        )
    return ObjectId(value)


def build_external_lookup(value: str, fields: tuple[str, ...]) -> Dict[str, Any]:
    lookups: List[Dict[str, Any]] = [{field: value} for field in fields]
    return {"$or": lookups}


async def resolve_product(db: AsyncIOMotorDatabase, product_id: str, create_if_missing: bool = False) -> Dict:
    if ObjectId.is_valid(product_id):
        product = await db.products.find_one({"_id": ObjectId(product_id)})
        if product:
            return product

    product = await db.products.find_one(build_external_lookup(product_id, PRODUCT_EXTERNAL_ID_FIELDS))
    if not product and create_if_missing and not ObjectId.is_valid(product_id):
        now = datetime.datetime.utcnow()
        product_doc = {
            "product_id": product_id,
            "external_id": product_id,
            "average_rating": 0.0,
            "review_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await db.products.insert_one(product_doc)
            product = await db.products.find_one({"_id": result.inserted_id})
        except DuplicateKeyError:
            product = await db.products.find_one(build_external_lookup(product_id, PRODUCT_EXTERNAL_ID_FIELDS))

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


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
        return object_id

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
        "product_id": str(review["product_id"]),
        "user_id": str(review["user_id"]),
        "username": review["username"],
        "rating": review["rating"],
        "comment": review["comment"],
        "images": review.get("images", []),
        "created_at": review["created_at"],
    }


async def get_product_rating_summary(db: AsyncIOMotorDatabase, product_id: Any, is_external: bool = False) -> Dict:
    match_field = "product_external_id" if is_external else "product_id"
    pipeline = [
        {"$match": {match_field: product_id}},
        {
            "$group": {
                "_id": f"${match_field}",
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
    try:
        product = await resolve_product(db, review.product_id, create_if_missing=True)
        product_id = product["_id"]
    except HTTPException:
        # Fallback if product resolution fails but we still want to allow review
        product_id = review.product_id

    user_id = await resolve_user_id(db, review.user_id, review.username)

    review_doc = {
        "product_id": product_id,
        "user_id": user_id,
        "product_external_id": review.product_id,
        "user_external_id": review.user_id,
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

    if isinstance(product_id, ObjectId):
        await sync_product_review_stats(db, product_id)
        
    created_review = await db.reviews.find_one({"_id": result.inserted_id})
    return serialize_review(created_review)


async def get_reviews_by_product(
    db: AsyncIOMotorDatabase,
    product_id: str,
    page: int,
    limit: int,
) -> Dict:
    try:
        product = await resolve_product(db, product_id)
        product_internal_id = product["_id"]
        is_external = False
        lookup_id = product_internal_id
    except HTTPException:
        # If product not found in 'products' collection, look up by external_id in reviews
        product_internal_id = product_id
        is_external = True
        lookup_id = product_id

    skip = (page - 1) * limit
    match_query = {"product_external_id": product_id} if is_external else {"product_id": lookup_id}
    
    cursor = (
        db.reviews.find(match_query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    reviews: List[Dict] = [serialize_review(review) async for review in cursor]
    summary = await get_product_rating_summary(db, lookup_id, is_external=is_external)
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
