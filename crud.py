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

def create_address(db: Session, address: schemas.AddressCreate):
    db_address = models.Address(**address.dict())
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

def get_user_addresses(db: Session, user_id: int):
    return db.query(models.Address).filter(models.Address.user_id == user_id).all()

def create_order(db: Session, order: schemas.OrderCreate):
    # 1. Get unique product IDs and sort them to prevent deadlocks
    product_ids = sorted(list(set(item.product_id for item in order.items)))

    try:
        # 2. Lock product rows
        products = db.query(models.Product).filter(
            models.Product.id.in_(product_ids)
        ).with_for_update().all()

        product_map = {p.id: p for p in products}

        # 3. Validate existence and stock
        for item in order.items:
            if item.product_id not in product_map:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            
            product = product_map[item.product_id]
            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient stock for product {product.name} (ID: {product.id})"
                )

        # 4. Create Order
        db_order = models.Order(
            user_id=order.user_id,
            address_id=order.address_id,
            payment_method=order.payment_method,
            total_price=0,
            status="pending"
        )
        db.add(db_order)
        db.flush() # Get order.id

        total_price = 0
        for item in order.items:
            product = product_map[item.product_id]
            item_total = product.price * item.quantity
            total_price += item_total

            # Create OrderItem
            db_item = models.OrderItem(
                order_id=db_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=product.price
            )
            db.add(db_item)

            # Update Stock
            product.stock -= item.quantity

        db_order.total_price = total_price

        # 5. Create Payment
        db_payment = models.Payment(
            order_id=db_order.id,
            method=order.payment_method,
            status="success"
        )
        db.add(db_payment)

        db.commit()
        db.refresh(db_order)
        return db_order

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
