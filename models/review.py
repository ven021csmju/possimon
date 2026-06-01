import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wine_id": 123,
                "user_id": "u001",
                "username": "ven",
                "rating": 5,
                "comment": "ดีมาก",
                "images": [],
            }
        }
    )

    wine_id: int = Field(..., gt=0)
    user_id: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=1, max_length=2000)
    images: List[str] = Field(default_factory=list)
    videos: List[str] = Field(default_factory=list)


class ReviewOut(BaseModel):
    id: str
    wine_id: int
    user_id: str
    username: str
    rating: int
    comment: str
    images: List[str]
    videos: List[str] = []
    created_at: datetime.datetime


class WineReviewSummary(BaseModel):
    wine_id: int
    average_rating: float
    review_count: int


class ReviewListOut(WineReviewSummary):
    page: int
    limit: int
    total_pages: int
    reviews: List[ReviewOut]
