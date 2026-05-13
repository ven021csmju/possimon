from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import crud
import schemas
import models
from auth.dependencies import get_db, get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.post("/addresses", response_model=schemas.AddressOut)
def create_address(
    address: schemas.AddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_address(db, address, current_user.id)

@router.get("/{user_id}/addresses", response_model=List[schemas.AddressOut])
def get_user_addresses(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "manager"] and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this resource")
    return crud.get_user_addresses(db, user_id)
