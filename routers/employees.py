from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import schemas
import models
from auth.dependencies import get_db, RoleChecker
from services import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])

# Only Admins can manage employees
admin_only = RoleChecker(["admin"])

@router.get("", response_model=List[schemas.EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):
    return employee_service.get_employees(db)

@router.post("", response_model=schemas.EmployeeOut)
def create_employee(
    employee: schemas.EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):
    return employee_service.create_employee(db, employee)

@router.put("/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(
    employee_id: int,
    employee: schemas.EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):
    return employee_service.update_employee(db, employee_id, employee)

@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):
    return employee_service.delete_employee(db, employee_id)
