import os
import logging

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

async def create_mongo_indexes():
    if db is None:
        logger.warning("Skipping MongoDB index creation: No database connection.")
        return
        
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
