from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    username = Column(String, unique=True, index=True)
    password = Column(String, nullable=True) # Allow null for Google Users
    role = Column(String, default="user")  # 👈 admin / user
    is_social = Column(Boolean, default=False) # Track if from Google/Social

class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    address_line = Column(String)
    province = Column(String)
    district = Column(String)
    subdistrict = Column(String)
    postal_code = Column(String)
    country = Column(String)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)
    stock = Column(Integer)
    type = Column(String)  # discriminator: 'product' or 'wine'

    __mapper_args__ = {
        "polymorphic_identity": "product",
        "polymorphic_on": type,
    }

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    address_id = Column(Integer, ForeignKey("addresses.id"))
    total_price = Column(Float)
    status = Column(String, default="pending")
    payment_method = Column(String)
    stripe_session_id = Column(String, nullable=True) # For Stripe Payment tracking
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price = Column(Float)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    method = Column(String)
    status = Column(String)
    paid_at = Column(DateTime, default=datetime.datetime.utcnow)

class Country(Base):
    __tablename__ = "countries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    regions = relationship("Region", back_populates="country", cascade="all, delete-orphan")
    wineries = relationship("Winery", back_populates="country")
    wines = relationship("Wine", back_populates="country")

class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id", ondelete="CASCADE"))
    country = relationship("Country", back_populates="regions")
    wineries = relationship("Winery", back_populates="region")
    wines = relationship("Wine", back_populates="region")

class Winery(Base):
    __tablename__ = "wineries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"))
    region_id = Column(Integer, ForeignKey("regions.id"))
    country = relationship("Country", back_populates="wineries")
    region = relationship("Region", back_populates="wineries")
    wines = relationship("Wine", back_populates="winery")

class Grape(Base):
    __tablename__ = "grapes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    wines = relationship("Wine", secondary="wine_grapes", back_populates="grapes")

class WineGrape(Base):
    __tablename__ = "wine_grapes"
    wine_id = Column(Integer, ForeignKey("wines.id", ondelete="CASCADE"), primary_key=True)
    grape_id = Column(Integer, ForeignKey("grapes.id", ondelete="CASCADE"), primary_key=True)

class Wine(Product):
    __tablename__ = "wines"
    id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    designation = Column(String(255))
    winery_id = Column(Integer, ForeignKey("wineries.id"))
    region_id = Column(Integer, ForeignKey("regions.id"))
    country_id = Column(Integer, ForeignKey("countries.id"))
    wine_type = Column(String(50))  # red, white, sparkling
    vintage = Column(Integer)
    alcohol = Column(Float)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    winery = relationship("Winery", back_populates="wines")
    region = relationship("Region", back_populates="wines")
    country = relationship("Country", back_populates="wines")
    grapes = relationship("Grape", secondary="wine_grapes", back_populates="wines")
    ratings = relationship("Rating", back_populates="wine", cascade="all, delete-orphan")

    __mapper_args__ = {
        "polymorphic_identity": "wine",
    }

class Rating(Base):
    __tablename__ = "ratings"
    id = Column(Integer, primary_key=True, index=True)
    wine_id = Column(Integer, ForeignKey("wines.id", ondelete="CASCADE"))
    score = Column(Float)  # e.g., 87
    taster_name = Column(String(100))
    review = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    wine = relationship("Wine", back_populates="ratings")
