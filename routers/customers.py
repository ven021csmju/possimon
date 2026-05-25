from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import schemas
import models
from auth.dependencies import get_db, get_current_user, RoleChecker

router = APIRouter(prefix="/customers", tags=["customers"])
admin_manager_only = RoleChecker(["admin", "manager"])

@router.get("", response_model=List[schemas.UserOut])
def list_customers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_manager_only)
):
    return db.query(models.User).filter(models.User.role == "customer").all()

@router.get("/addresses", response_model=List[schemas.AddressOut])
def get_my_addresses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Address).filter(models.Address.user_id == current_user.id).all()

@router.post("/addresses", response_model=schemas.AddressOut)
def add_address(
    address: schemas.AddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_address = models.Address(
        **address.dict(),
        user_id=current_user.id
    )
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address
