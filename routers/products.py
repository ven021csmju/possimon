from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import crud
import schemas
from auth.dependencies import get_db, RoleChecker

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
