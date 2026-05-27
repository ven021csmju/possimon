from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from database_nosql import get_mongo_db
from models.review import ReviewCreate, ReviewListOut, ReviewOut
from services import review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    return await review_service.create_review(db, review)


@router.get("/product/{product_id}", response_model=ReviewListOut)
async def get_product_reviews(
    product_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    return await review_service.get_reviews_by_product(db, product_id, page, limit)
