from fastapi import APIRouter, Depends, Query, status, UploadFile, File
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


@router.post("/media", status_code=status.HTTP_201_CREATED)
async def upload_review_media(
    file: UploadFile = File(...),
):
    is_video = file.content_type.startswith("video/")
    url = await review_service.upload_review_media(file, is_video)
    return {"url": url}


@router.get("/product/{wine_id}", response_model=ReviewListOut)
async def get_product_reviews(
    wine_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    return await review_service.get_reviews_by_product(db, wine_id, page, limit)
