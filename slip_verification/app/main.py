from fastapi import FastAPI
from app.api.v1.endpoints import payments
from app.core.config import settings
from app.db.session import Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(payments.router, prefix=f"{settings.API_V1_STR}/payments", tags=["payments"])

@app.get("/")
def root():
    return {"message": "Slip Verification Service is running"}
