from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
import datetime
import enum

# --- Enums from Models ---
class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    COMPLETED = "completed"

class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    PROMPTPAY = "promptpay"
    QR = "qr"
    CREDIT_CARD = "credit_card"
    TRANSFER = "transfer"

class OrderType(str, enum.Enum):
    POS = "pos"
    ONLINE = "online"

# --- Schemas ---

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    cost_price: float = Field(0.0, ge=0)
    selling_price: float = Field(..., gt=0)
    price: float = Field(..., gt=0) # Legacy
    stock: int = Field(..., ge=0)
    low_stock_alert: int = Field(10, ge=0)
    image_url: Optional[str] = None
    status: str = "active"

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    cost_price: Optional[float] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, gt=0)
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    low_stock_alert: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None
    status: Optional[str] = None

class StockRefill(BaseModel):
    quantity: int = Field(..., gt=0, description="Amount to add to current stock")

class ProductImageOut(BaseModel):
    id: int
    product_id: int
    image_url: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ProductOut(BaseModel):
    id: int
    name: str
    sku: Optional[str]
    barcode: Optional[str]
    selling_price: float
    price: float
    stock: int
    type: str
    images: List[ProductImageOut] = []

    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="The unique database ID of the product")
    sku: Optional[str] = Field(None, description="Optional SKU for reference")
    quantity: int = Field(..., gt=0)
    price: Optional[float] = None

class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float
    product: ProductOut

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    user_id: Optional[int] = None # For compatibility, though we use token
    address_id: Optional[int] = Field(None, gt=0) # Optional for POS
    payment_method: PaymentMethod
    order_type: OrderType = OrderType.ONLINE
    items: List[OrderItemCreate] = Field(..., min_length=1)
    total_amount: Optional[float] = None 
    received_amount: Optional[float] = None
    change_amount: Optional[float] = None

class OrderOut(BaseModel):
    id: int
    user_id: int
    address_id: Optional[int]
    total_price: float
    total_amount: Optional[float] = None # Duplicate for frontend compatibility
    status: OrderStatus
    payment_method: PaymentMethod
    order_type: OrderType
    created_at: datetime.datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        # Ensure total_amount is populated from total_price
        data = super().from_orm(obj)
        if hasattr(data, 'total_price') and not data.total_amount:
            data.total_amount = data.total_price
        return data

class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=1, max_length=30)
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)

class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=1, max_length=30)
    password: Optional[str] = Field(None, min_length=8, max_length=128)

class LoginRequest(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    username: str
    role: str

    class Config:
        from_attributes = True

class EmployeeCreate(UserCreate):
    role: str = Field(..., pattern="^(admin|manager|cashier)$")

class EmployeeUpdate(UserUpdate):
    role: Optional[str] = Field(None, pattern="^(admin|manager|cashier)$")

class EmployeeOut(UserOut):
    pass

class AddressCreate(BaseModel):
    address_line: str = Field(..., min_length=1, max_length=255)
    subdistrict: str = Field(..., min_length=1, max_length=100)
    district: str = Field(..., min_length=1, max_length=100)
    province: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=1, max_length=100)

class AddressOut(BaseModel):
    id: int
    user_id: int
    address_line: str
    subdistrict: str
    district: str
    province: str
    postal_code: str
    country: str

    class Config:
        from_attributes = True

# Wine Related Schemas

class CountryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class CountryOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class RegionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    country_id: int = Field(..., gt=0)

class RegionOut(BaseModel):
    id: int
    name: str
    country_id: int
    class Config:
        from_attributes = True

class WineryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    country_id: int = Field(..., gt=0)
    region_id: int = Field(..., gt=0)

class WineryOut(BaseModel):
    id: int
    name: str
    country_id: int
    region_id: int
    class Config:
        from_attributes = True

class GrapeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class GrapeOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class WineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    designation: Optional[str] = Field(default=None, max_length=255)
    winery_id: int = Field(..., gt=0)
    region_id: int = Field(..., gt=0)
    country_id: int = Field(..., gt=0)
    wine_type: Optional[str] = Field(default=None, max_length=50)
    vintage: Optional[int] = Field(default=None, ge=1000, le=9999)
    alcohol: Optional[float] = Field(default=None, ge=0, le=100)
    description: Optional[str] = None
    food_pairing: Optional[str] = Field(default=None, max_length=500)
    sweetness: Optional[int] = Field(default=None, ge=1, le=5)
    bottle_size_ml: Optional[int] = Field(default=750, ge=187, le=3000)
    tasting_notes: Optional[str] = None
    aging_notes: Optional[str] = Field(default=None, max_length=255)
    grape_ids: List[int] = Field(default_factory=list)

class WineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    designation: Optional[str] = Field(None, max_length=255)
    winery_id: Optional[int] = Field(None, gt=0)
    region_id: Optional[int] = Field(None, gt=0)
    country_id: Optional[int] = Field(None, gt=0)
    wine_type: Optional[str] = Field(None, max_length=50)
    vintage: Optional[int] = Field(None, ge=1000, le=9999)
    alcohol: Optional[float] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    food_pairing: Optional[str] = Field(None, max_length=500)
    sweetness: Optional[int] = Field(None, ge=1, le=5)
    bottle_size_ml: Optional[int] = Field(None, ge=187, le=3000)
    tasting_notes: Optional[str] = None
    aging_notes: Optional[str] = Field(None, max_length=255)
    grape_ids: Optional[List[int]] = None

class WineOut(ProductOut):
    designation: Optional[str] = None
    wine_type: Optional[str] = None
    vintage: Optional[int] = None
    alcohol: Optional[float] = None
    description: Optional[str] = None
    food_pairing: Optional[str] = None
    sweetness: Optional[int] = None
    bottle_size_ml: Optional[int] = None
    tasting_notes: Optional[str] = None
    aging_notes: Optional[str] = None
    winery: Optional[WineryOut] = None
    region: Optional[RegionOut] = None
    country: Optional[CountryOut] = None
    grapes: List[GrapeOut] = []
    class Config:
        from_attributes = True

class RatingCreate(BaseModel):
    wine_id: int = Field(..., gt=0)
    score: float = Field(..., ge=0, le=100)
    review: Optional[str] = None
    taster_name: Optional[str] = Field(default=None, max_length=100)

class RatingOut(BaseModel):
    id: int
    wine_id: int
    score: float
    review: Optional[str] = None
    taster_name: Optional[str] = None
    class Config:
        from_attributes = True
