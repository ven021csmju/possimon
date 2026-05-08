from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from auth.dependencies import get_db, get_current_user, RoleChecker
from services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=schemas.OrderOut)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return order_service.create_order(db, order, current_user.id)

@router.get("", response_model=List[schemas.OrderOut])
def get_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["admin", "manager", "cashier"])),
):
    return db.query(models.Order).all()

@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if current_user.role not in ["admin", "manager"] and db_order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this resource")
        
    return db_order
