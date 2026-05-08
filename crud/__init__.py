from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import models, schemas

def get_products(db: Session):
    return db.query(models.Product).all()

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def create_address(db: Session, address: schemas.AddressCreate, user_id: int):
    db_address = models.Address(**address.dict(), user_id=user_id)
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

def get_user_addresses(db: Session, user_id: int):
    return db.query(models.Address).filter(models.Address.user_id == user_id).all()

# Wine Related CRUD

def create_country(db: Session, country: schemas.CountryCreate):
    db_country = models.Country(**country.dict())
    db.add(db_country)
    db.commit()
    db.refresh(db_country)
    return db_country

def get_countries(db: Session):
    return db.query(models.Country).all()

def create_region(db: Session, region: schemas.RegionCreate):
    db_region = models.Region(**region.dict())
    db.add(db_region)
    db.commit()
    db.refresh(db_region)
    return db_region

def get_regions(db: Session):
    return db.query(models.Region).all()

def create_winery(db: Session, winery: schemas.WineryCreate):
    db_winery = models.Winery(**winery.dict())
    db.add(db_winery)
    db.commit()
    db.refresh(db_winery)
    return db_winery

def get_wineries(db: Session):
    return db.query(models.Winery).all()

def create_grape(db: Session, grape: schemas.GrapeCreate):
    db_grape = models.Grape(**grape.dict())
    db.add(db_grape)
    db.commit()
    db.refresh(db_grape)
    return db_grape

def get_grapes(db: Session):
    return db.query(models.Grape).all()

def create_wine(db: Session, wine: schemas.WineCreate):
    wine_data = wine.dict(exclude={"grape_ids"})
    db_wine = models.Wine(**wine_data)

    if wine.grape_ids:
        grapes = db.query(models.Grape).filter(models.Grape.id.in_(wine.grape_ids)).all()
        db_wine.grapes = grapes

    db.add(db_wine)
    db.commit()
    db.refresh(db_wine)
    return db_wine

def get_wines(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Wine).options(
        joinedload(models.Wine.winery),
        joinedload(models.Wine.region),
        joinedload(models.Wine.country),
        joinedload(models.Wine.grapes)
    ).offset(skip).limit(limit).all()

def create_rating(db: Session, rating: schemas.RatingCreate):
    wine = db.query(models.Wine).filter(models.Wine.id == rating.wine_id).first()
    if not wine:
        raise HTTPException(status_code=404, detail="Wine not found")

    db_rating = models.Rating(**rating.dict())
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating

def get_wine_ratings(db: Session, wine_id: int):
    return db.query(models.Rating).filter(models.Rating.wine_id == wine_id).all()
