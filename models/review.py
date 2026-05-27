import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": "p001",
                "user_id": "u001",
                "username": "ven",
                "rating": 5,
                "comment": "ดีมาก",
                "images": [],
            }
        }
    )

    product_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=1, max_length=2000)
    images: List[str] = Field(default_factory=list)


class ReviewOut(BaseModel):
    id: str
    product_id: str
    user_id: str
    username: str
    rating: int
    comment: str
    images: List[str]
    created_at: datetime.datetime


class ProductReviewSummary(BaseModel):
    product_id: str
    average_rating: float
    review_count: int


class ReviewListOut(ProductReviewSummary):
    page: int
    limit: int
    total_pages: int
    reviews: List[ReviewOut]
