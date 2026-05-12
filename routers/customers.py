from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import schemas
import models
from auth.dependencies import get_db, RoleChecker

router = APIRouter(prefix="/customers", tags=["customers"])
admin_manager_only = RoleChecker(["admin", "manager"])

@router.get("", response_model=List[schemas.UserOut])
def list_customers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_manager_only)
):
    return db.query(models.User).filter(models.User.role == "customer").all()
