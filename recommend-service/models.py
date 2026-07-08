import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String)
    created_at = Column(DateTime)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    sku = Column(String)
    barcode = Column(String)
    selling_price = Column(Float)
    price = Column(Float)
    stock = Column(Integer)
    status = Column(String)
    type = Column(String)
    created_at = Column(DateTime)


class Wine(Base):
    __tablename__ = "wines"

    id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    designation = Column(String)
    wine_type = Column(String)
    vintage = Column(Integer)
    alcohol = Column(Float)
    description = Column(String)
    food_pairing = Column(String)
    sweetness = Column(Integer)
    bottle_size_ml = Column(Integer)
    tasting_notes = Column(String)
    aging_notes = Column(String)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    status = Column(String)
    total_price = Column(Float)
    created_at = Column(DateTime)

    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    quantity = Column(Integer)
    price = Column(Float)

    order = relationship("Order", back_populates="items")


class UserLog(Base):
    __tablename__ = "user_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    event_type = Column(String, index=True)
    query = Column(String)
    keyword = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DailyUserStats(Base):
    __tablename__ = "daily_user_stats"

    id = Column(Integer, primary_key=True, index=True)
    stat_date = Column(Date, index=True)
    user_id = Column(Integer, index=True)
    event_type = Column(String, index=True)
    product_id = Column(Integer, index=True)
    event_count = Column(Integer)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_recommendations_user_product"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), index=True, nullable=False)
    score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
