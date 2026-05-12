import requests
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
import crud
import schemas
import models
from auth.dependencies import get_db, RoleChecker
from core.config import settings

router = APIRouter(prefix="/wines", tags=["wines"])
admin_required = RoleChecker(["admin"])

@router.post("/countries", response_model=schemas.CountryOut)
def create_country(
    country: schemas.CountryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_required),
):
    return crud.create_country(db, country)

@router.get("/countries", response_model=List[schemas.CountryOut])
def get_countries(db: Session = Depends(get_db)):
    return crud.get_countries(db)

@router.post("/regions", response_model=schemas.RegionOut)
def create_region(
    region: schemas.RegionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_required),
):
    return crud.create_region(db, region)

@router.get("/regions", response_model=List[schemas.RegionOut])
def get_regions(db: Session = Depends(get_db)):
    return crud.get_regions(db)

@router.post("/wineries", response_model=schemas.WineryOut)
def create_winery(
    winery: schemas.WineryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_required),
):
    return crud.create_winery(db, winery)

@router.get("/wineries", response_model=List[schemas.WineryOut])
def get_wineries(db: Session = Depends(get_db)):
    return crud.get_wineries(db)

@router.post("/grapes", response_model=schemas.GrapeOut)
def create_grape(
    grape: schemas.GrapeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_required),
):
    return crud.create_grape(db, grape)

@router.get("/grapes", response_model=List[schemas.GrapeOut])
def get_grapes(db: Session = Depends(get_db)):
    return crud.get_grapes(db)

@router.post("", response_model=schemas.WineOut)
def create_wine(
    wine: schemas.WineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_required),
):
    return crud.create_wine(db, wine)

@router.get("", response_model=List[schemas.WineOut])
def get_wines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return crud.get_wines(db, skip=skip, limit=limit)

@router.put("/{wine_id}", response_model=schemas.WineOut)
def update_wine(
    wine_id: int,
    wine: schemas.WineUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["admin", "manager"])),
):
    return crud.update_wine(db, wine_id, wine)

@router.post("/ratings", response_model=schemas.RatingOut)
def create_rating(
    rating: schemas.RatingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_required),
):
    return crud.create_rating(db, rating)

@router.get("/{wine_id}/ratings", response_model=List[schemas.RatingOut])
def get_wine_ratings(wine_id: int, db: Session = Depends(get_db)):
    return crud.get_wine_ratings(db, wine_id)
    
@router.get("/external-api")
def get_wine_external(current_user: models.User = Depends(admin_required)):
    try:
        url = "https://api.grapeminds.eu/public/v1/wines"
        headers = {
            "Authorization": f"Bearer {settings.API_KEY}"
        }
        response = requests.get(url, headers=headers)
        return {
            "status": response.status_code,
            "data": response.json()
        }
    except Exception as e:
        return {"error": str(e)}
