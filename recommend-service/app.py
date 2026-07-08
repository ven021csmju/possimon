from typing import List

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Recommendation


app = FastAPI(title="PoSimon Recommendation Service", version="1.0.0")


class RecommendationOut(BaseModel):
    product_id: int
    score: float

    class Config:
        from_attributes = True


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine, tables=[Recommendation.__table__])


@app.get("/health")
def health_check():
    return {"status": "online", "service": "recommendations"}


@app.get("/recommendations/{user_id}", response_model=List[RecommendationOut])
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == user_id)
        .order_by(Recommendation.score.desc(), Recommendation.created_at.desc())
        .limit(20)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No recommendations found for this user")
    return rows
