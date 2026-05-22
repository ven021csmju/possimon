from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import List
import crud
import schemas
from auth.dependencies import get_db, RoleChecker
from services import notification_service

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=List[schemas.ProductOut])
def get_products(db: Session = Depends(get_db)):
    return crud.get_products(db)

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
