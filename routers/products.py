from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
import crud
import schemas
import models
from auth.dependencies import get_db, RoleChecker
from database_nosql import get_mongo_db
from services import review_service, notification_service

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=List[schemas.ProductOut])
async def get_products(
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    products = crud.get_products(db)
    product_ids = [p.id for p in products]
    stats_map = await review_service.get_bulk_rating_summaries(mongo_db, product_ids)
    
    results = []
    for p in products:
        p_out = schemas.ProductOut.from_orm(p)
        stats = stats_map.get(p.id, {"average_rating": 0.0, "review_count": 0})
        p_out.average_rating = stats["average_rating"]
        p_out.review_count = stats["review_count"]
        results.append(p_out)
    return results

@router.get("/{product_id}", response_model=schemas.ProductOut)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    stats = await review_service.get_rating_summary(mongo_db, product_id)
    p_out = schemas.ProductOut.from_orm(product)
    p_out.average_rating = stats["average_rating"]
    p_out.review_count = stats["review_count"]
    return p_out

@router.post("", response_model=schemas.ProductOut)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user = Depends(RoleChecker(["admin", "manager"])),
):
    return crud.create_product(db, product)

@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    product: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(RoleChecker(["admin", "manager"])),
):
    return crud.update_product(db, product_id, product)

@router.post("/{product_id}/refill", response_model=schemas.ProductOut)
def refill_stock(
    product_id: int,
    refill: schemas.StockRefill,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(RoleChecker(["admin", "manager", "cashier"])),
):
    product = crud.refill_stock(db, product_id, refill)
    background_tasks.add_task(notification_service.notify_low_stock, product)
    return product
