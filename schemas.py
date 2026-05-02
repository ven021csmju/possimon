from pydantic import BaseModel, EmailStr
from typing import List, Optional
import datetime

class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int

class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    type: str

    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float
    product: ProductOut

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    user_id: int
    address_id: int
    payment_method: str
    items: List[OrderItemCreate]

class OrderOut(BaseModel):
    id: int
    user_id: int
    address_id: int
    total_price: float
    status: str
    payment_method: str
    created_at: datetime.datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    username: str

    class Config:
        from_attributes = True

class AddressCreate(BaseModel):
    user_id: int
    address_line: str
    subdistrict: str
    district: str
    province: str
    postal_code: str
    country: str

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
    name: str

class CountryOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class RegionCreate(BaseModel):
    name: str
    country_id: int

class RegionOut(BaseModel):
    id: int
    name: str
    country_id: int
    class Config:
        from_attributes = True

class WineryCreate(BaseModel):
    name: str
    country_id: int
    region_id: int

class WineryOut(BaseModel):
    id: int
    name: str
    country_id: int
    region_id: int
    class Config:
        from_attributes = True

class GrapeCreate(BaseModel):
    name: str

class GrapeOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class WineCreate(BaseModel):
    name: str
    price: float
    stock: int
    designation: Optional[str] = None
    winery_id: int
    region_id: int
    country_id: int
    wine_type: Optional[str] = None
    vintage: Optional[int] = None
    alcohol: Optional[float] = None
    description: Optional[str] = None
    grape_ids: List[int] = []

class WineOut(ProductOut):
    designation: Optional[str] = None
    wine_type: Optional[str] = None
    vintage: Optional[int] = None
    alcohol: Optional[float] = None
    description: Optional[str] = None
    winery: Optional[WineryOut] = None
    region: Optional[RegionOut] = None
    country: Optional[CountryOut] = None
    grapes: List[GrapeOut] = []
    class Config:
        from_attributes = True

class RatingCreate(BaseModel):
    wine_id: int
    score: float
    review: Optional[str] = None
    taster_name: Optional[str] = None

class RatingOut(BaseModel):
    id: int
    wine_id: int
    score: float
    review: Optional[str] = None
    taster_name: Optional[str] = None
    class Config:
        from_attributes = True
