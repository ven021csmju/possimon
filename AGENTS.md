# AGENTS.md — PoSimon Backend Conventions

AI agents (Gemini, Claude, OpenCode) must follow these conventions when generating code for this project.

## Project Overview
- **Stack**: FastAPI + SQLAlchemy + PostgreSQL (SQLite for local dev)
- **Architecture**: Layered — `routers/` → `services/` → `crud/` → `models/`
- **Auth**: JWT Bearer token via `HTTPBearer`, role-based access via `RoleChecker`

## Directory Structure & Responsibility

| Directory | Role |
|-----------|------|
| `routers/` | HTTP endpoints, dependency injection only |
| `services/` | Business logic (complex operations, transactions) |
| `crud/` | Simple DB queries (no business logic) |
| `models/` | SQLAlchemy ORM models (all in `__init__.py`) |
| `schemas/` | Pydantic request/response schemas (all in `__init__.py`) |
| `auth/` | Auth dependencies, JWT, OAuth |
| `core/` | Config, security helpers |

## Naming Conventions
- **Files**: snake_case, plural (`products.py`, `order_service.py`)
- **Router prefix**: plural nouns (`/products`, `/wines`)
- **Functions/Variables**: snake_case
- **Classes**: PascalCase
- **DB models**: Singular PascalCase (`User`, `OrderItem`)
- **API tags**: lowercase plural

## Code Patterns

### Router Pattern
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import crud, schemas
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
```

### Service Pattern (transactional logic)
```python
from sqlalchemy.orm import Session
from fastapi import HTTPException
import models, schemas

def create_order(db: Session, order: schemas.OrderCreate, user_id: int):
    try:
        # Lock rows with with_for_update()
        products = db.query(models.Product).filter(
            models.Product.id.in_(product_ids)
        ).with_for_update().all()

        # ... business logic ...

        db.commit()
        db.refresh(db_order)
        return db_order
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

### CRUD Pattern
```python
def get_products(db: Session):
    return db.query(models.Product).all()

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product
```

### Schema Pattern (Pydantic v2)
- Use `from_attributes = True` in Config for ORM mode
- Use `model_dump()` instead of `dict()` (Pydantic v2)
- Prefer `Field(...)` for validation
```python
class ProductOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True
```

### Model Pattern (SQLAlchemy)
- All models in `models/__init__.py`
- Use `relationship()` with `back_populates`
- Timestamp fields: `created_at = Column(DateTime, default=datetime.datetime.utcnow)`

## Imports Rules
- **No relative imports** — always absolute (`import models`)
- Prefer top-level imports: `import crud`, `import schemas`, `import models`
- Import `Session` from `sqlalchemy.orm`, not `sqlalchemy`

## Error Handling
- Use `HTTPException` from `fastapi` (not custom exceptions)
- Return appropriate status codes: 400 (bad request), 404 (not found), 401 (unauthorized), 403 (forbidden), 500 (server error)

## Auth
- `get_db()` yields `SessionLocal` session
- `RoleChecker(["admin"])` for admin-only endpoints
- `Depends(security)` where `security = HTTPBearer()`

## General Rules
- Keep files focused and short (one resource per router file)
- No comments unless explaining complex logic
- Use `with_for_update()` for stock/transactional operations
- All enum models use `class MyEnum(enum.Enum)` with lowercase string values
- Schema enums mirror model enums but inherit from `str, enum.Enum`
