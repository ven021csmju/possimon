from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from auth.dependencies import get_db, get_current_user, RoleChecker
from services import order_service, notification_service
from exceptions.not_found_exception import NotFoundException
from exceptions.auth_exception import AuthException

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=schemas.OrderOut)
def create_order(
    order: schemas.OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_order, affected_products = order_service.create_order(db, order, current_user.id)
    background_tasks.add_task(
        notification_service.post_order_created_side_effects,
        db_order,
        affected_products,
    )
    return db_order

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
        raise NotFoundException(message="Order not found", code="ORDER_NOT_FOUND")
    
    if current_user.role not in ["admin", "manager"] and db_order.user_id != current_user.id:
        raise AuthException(
            message="You do not have permission to access this resource",
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN
        )
        
    return db_order
