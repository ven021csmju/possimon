import os
import logging

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

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

async def create_mongo_indexes():
    if db is None:
        logger.warning("Skipping MongoDB index creation: No database connection.")
        return
        
    await db.reviews.create_index(
        [("product_id", 1), ("user_id", 1)],
        unique=True,
        name="uniq_review_product_user",
    )
    await db.reviews.create_index(
        [("product_id", 1), ("created_at", -1)],
        name="idx_reviews_product_created_at",
    )
    await db.reviews.create_index([("user_id", 1)], name="idx_reviews_user")
    await db.reviews.create_index([("product_external_id", 1)], name="idx_reviews_product_external_id")
    await db.reviews.create_index([("user_external_id", 1)], name="idx_reviews_user_external_id")
    await db.users.create_index([("external_id", 1)], unique=True, sparse=True, name="uniq_users_external_id")
    await db.products.create_index([("product_id", 1)], unique=True, sparse=True, name="uniq_products_product_id")
    await db.products.create_index([("sku", 1)], sparse=True, name="idx_products_sku")
    await db.products.create_index([("code", 1)], sparse=True, name="idx_products_code")
    await db.products.create_index([("external_id", 1)], unique=True, sparse=True, name="uniq_products_external_id")
    await db.products.create_index([("review_count", -1)], name="idx_products_review_count")
    await db.products.create_index([("average_rating", -1)], name="idx_products_average_rating")
