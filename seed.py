from sqlalchemy.orm import Session
from models import Product, User, Address, OrderStatus, PaymentMethod, OrderType
import models
from core.security import hash_password

def seed_data(db: Session):
    # Check if users already exist
    if db.query(User).first():
        print("Data already seeded.")
        return

    # 1. Users
    admin = User(first_name="Admin", last_name="User", email="admin@example.com", phone="1234567890", username="admin", password=hash_password("admin123"), role="admin")
    cashier = User(first_name="Somsak", last_name="Cashier", email="cashier@example.com", phone="0812345678", username="cashier01", password=hash_password("cashier123"), role="cashier")
    john = User(first_name="John", last_name="Doe", email="john@example.com", phone="0987654321", username="john_doe", password=hash_password("password123"), role="customer")
    db.add_all([admin, cashier, john])
    db.commit()

    # 2. Addresses
    addr1 = Address(user_id=admin.id, address_line="123 Admin St", province="Bangkok", district="Pathum Wan", subdistrict="Lumpini", postal_code="10330", country="Thailand")
    addr2 = Address(user_id=john.id, address_line="456 User Ave", province="Bangkok", district="Bang Rak", subdistrict="Silom", postal_code="10500", country="Thailand")
    db.add_all([addr1, addr2])
    db.commit()

    # 3. Regular Products
    products = [
        Product(
            name="Coke", 
            sku="COKE-001", 
            barcode="885000000001", 
            cost_price=15.0, 
            selling_price=20.0, 
            price=20.0, 
            stock=100, 
            type="product"
        ),
        Product(
            name="Pepsi", 
            sku="PEPSI-001", 
            barcode="885000000002", 
            cost_price=15.0, 
            selling_price=20.0, 
            price=20.0, 
            stock=100, 
            type="product"
        ),
        Product(
            name="Water", 
            sku="WATER-001", 
            barcode="885000000003", 
            cost_price=5.0, 
            selling_price=10.0, 
            price=10.0, 
            stock=200, 
            type="product"
        ),
    ]
    db.add_all(products)
    db.commit()

    # 4. Countries, Regions, Wineries, Grapes
    france = models.Country(name="France")
    italy = models.Country(name="Italy")
    db.add_all([france, italy])
    db.commit()

    bordeaux = models.Region(name="Bordeaux", country_id=france.id)
    tuscany = models.Region(name="Tuscany", country_id=italy.id)
    db.add_all([bordeaux, tuscany])
    db.commit()

    chateau_margaux = models.Winery(name="Château Margaux", country_id=france.id, region_id=bordeaux.id)
    antinori = models.Winery(name="Antinori", country_id=italy.id, region_id=tuscany.id)
    db.add_all([chateau_margaux, antinori])
    db.commit()

    cabernet = models.Grape(name="Cabernet Sauvignon")
    merlot = models.Grape(name="Merlot")
    db.add_all([cabernet, merlot])
    db.commit()

    # 5. Wines
    wine1 = models.Wine(
        name="Margaux 2015",
        sku="WINE-FR-001",
        barcode="300000000001",
        cost_price=800.0,
        selling_price=1200.0,
        price=1200.0,
        winery_id=chateau_margaux.id,
        region_id=bordeaux.id,
        country_id=france.id,
        wine_type="Red",
        vintage=2015,
        alcohol=13.5,
        stock=10,
        type="wine",
        description="A legendary vintage from Château Margaux."
    )
    wine1.grapes = [cabernet, merlot]

    wine2 = models.Wine(
        name="Tignanello 2018",
        sku="WINE-IT-001",
        barcode="800000000001",
        cost_price=100.0,
        selling_price=150.0,
        price=150.0,
        winery_id=antinori.id,
        region_id=tuscany.id,
        country_id=italy.id,
        wine_type="Red",
        vintage=2018,
        alcohol=14.0,
        stock=20,
        type="wine",
        description="Famous Super Tuscan wine."
    )
    db.add_all([wine1, wine2])
    db.commit()
