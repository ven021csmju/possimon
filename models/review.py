import datetime
from typing import List

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator


def validate_object_id(value: str) -> str:
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId")
    return value


class ReviewCreate(BaseModel):
    product_id: str
    user_id: str
    username: str = Field(..., min_length=1, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=1, max_length=2000)
    images: List[str] = Field(default_factory=list)

    @field_validator("product_id", "user_id")
    @classmethod
    def object_id_must_be_valid(cls, value: str) -> str:
        return validate_object_id(value)


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
