from sqlalchemy.orm import Session
from fastapi import HTTPException
import models, schemas
import logging
from core.security import hash_password

logger = logging.getLogger("possimon")

def get_employees(db: Session):
    return db.query(models.User).filter(models.User.role.in_(["admin", "manager", "cashier"])).all()

def create_employee(db: Session, employee: schemas.EmployeeCreate):
    # Check if email or username already exists
    if db.query(models.User).filter((models.User.email == employee.email) | (models.User.username == employee.username)).first():
        logger.warning(f"Employee creation failed: Email/Username {employee.email}/{employee.username} already exists")
        raise HTTPException(status_code=400, detail="Email or Username already exists")
    
    db_employee = models.User(
        first_name=employee.first_name,
        last_name=employee.last_name,
        email=employee.email,
        phone=employee.phone,
        username=employee.username,
        password=hash_password(employee.password),
        role=employee.role,
        is_social=False
    )
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    logger.info(f"New employee created: {db_employee.username} with role {db_employee.role}")
    return db_employee

def update_employee(db: Session, employee_id: int, employee_update: schemas.EmployeeUpdate):
    db_employee = db.query(models.User).filter(
        models.User.id == employee_id,
        models.User.role.in_(["admin", "manager", "cashier"])
    ).first()
    
    if not db_employee:
        logger.warning(f"Update failed: Employee {employee_id} not found")
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = employee_update.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password"] = hash_password(update_data["password"])
    
    for key, value in update_data.items():
        setattr(db_employee, key, value)
    
    db.commit()
    db.refresh(db_employee)
    logger.info(f"Employee updated: {db_employee.username}")
    return db_employee

def delete_employee(db: Session, employee_id: int):
    db_employee = db.query(models.User).filter(
        models.User.id == employee_id,
        models.User.role.in_(["admin", "manager", "cashier"])
    ).first()
    
    if not db_employee:
        logger.warning(f"Delete failed: Employee {employee_id} not found")
        raise HTTPException(status_code=404, detail="Employee not found")
    
    db.delete(db_employee)
    db.commit()
    logger.info(f"Employee deleted: ID {employee_id}")
    return {"message": "Employee deleted successfully"}
