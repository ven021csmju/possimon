import os
import requests
from dotenv import load_dotenv

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000/auth/success")

from fastapi import Depends, FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
import io
import qrcode
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from typing import List
from jose import jwt

import crud
import models
import schemas
from database import Base, SessionLocal, engine
from seed import seed_data
from auth import verify_password, create_access_token, hash_password, SECRET_KEY, ALGORITHM, oauth

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

@app.get("/")
def read_root():
    return {"status": "ok", "message": "PoSimon Backend is running"}

@app.get("/products", response_model=List[schemas.ProductOut])
def get_products(db: Session = Depends(get_db)):
    return crud.get_products(db)

@app.post("/products", response_model=schemas.ProductOut)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, product)

@app.post("/orders", response_model=schemas.OrderOut)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    return crud.create_order(db, order)

@app.get("/orders", response_model=List[schemas.OrderOut])
def get_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).all()

@app.get("/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@app.post("/addresses", response_model=schemas.AddressOut)
def create_address(address: schemas.AddressCreate, db: Session = Depends(get_db)):
    return crud.create_address(db, address)

@app.get("/users/{user_id}/addresses", response_model=List[schemas.AddressOut])
def get_user_addresses(user_id: int, db: Session = Depends(get_db)):
    return crud.get_user_addresses(db, user_id)

@app.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "user_id": user.id,
        "role": user.role
    })

    return {"access_token": token}

@app.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for("auth_google")
    # Fix for Render: Ensure redirect_uri uses https
    if "onrender.com" in str(redirect_uri):
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def auth_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

    # ✅ ใช้วิธีนี้แทน parse_id_token
    resp = await oauth.google.get(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        token=token
    )
    user_info = resp.json()

    email = user_info.get("email")

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        user = models.User(
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            email=email,
            username=email,
            password=hash_password("google_oauth_no_password"),
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token({
        "user_id": user.id,
        "role": user.role
    })

    return RedirectResponse(url=f"{FRONTEND_URL}?token={jwt_token}")

def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user exists by email first (for social/existing updates)
    existing_user = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if existing_user:
        # Update existing user info
        existing_user.first_name = user.first_name
        existing_user.last_name = user.last_name
        existing_user.phone = user.phone
        # Only update password if provided and not a social user
        if user.password and user.password != "google_oauth_no_password":
            existing_user.password = hash_password(user.password)
            existing_user.is_social = False
        
        db.commit()
        db.refresh(existing_user)
        return {
            "message": "user updated successfully",
            "user_id": existing_user.id
        }

    # Check if username exists
    existing_username = db.query(models.User).filter(
        models.User.username == user.username
    ).first()

    if existing_username:
        raise HTTPException(status_code=400, detail="Username already exists")

    try:
        new_user = models.User(
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone=user.phone,
            username=user.username,
            password=hash_password(user.password),
            role="user",
            is_social=False
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "message": "register success",
            "user_id": new_user.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Wine Related Endpoints

@app.post("/countries", response_model=schemas.CountryOut)
def create_country(country: schemas.CountryCreate, db: Session = Depends(get_db)):
    return crud.create_country(db, country)

@app.get("/countries", response_model=List[schemas.CountryOut])
def get_countries(db: Session = Depends(get_db)):
    return crud.get_countries(db)

@app.post("/regions", response_model=schemas.RegionOut)
def create_region(region: schemas.RegionCreate, db: Session = Depends(get_db)):
    return crud.create_region(db, region)

@app.get("/regions", response_model=List[schemas.RegionOut])
def get_regions(db: Session = Depends(get_db)):
    return crud.get_regions(db)

@app.post("/wineries", response_model=schemas.WineryOut)
def create_winery(winery: schemas.WineryCreate, db: Session = Depends(get_db)):
    return crud.create_winery(db, winery)

@app.get("/wineries", response_model=List[schemas.WineryOut])
def get_wineries(db: Session = Depends(get_db)):
    return crud.get_wineries(db)

@app.post("/grapes", response_model=schemas.GrapeOut)
def create_grape(grape: schemas.GrapeCreate, db: Session = Depends(get_db)):
    return crud.create_grape(db, grape)

@app.get("/grapes", response_model=List[schemas.GrapeOut])
def get_grapes(db: Session = Depends(get_db)):
    return crud.get_grapes(db)

@app.post("/wines", response_model=schemas.WineOut)
def create_wine(wine: schemas.WineCreate, db: Session = Depends(get_db)):
    return crud.create_wine(db, wine)

@app.get("/wines", response_model=List[schemas.WineOut])
def get_wines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_wines(db, skip=skip, limit=limit)

@app.post("/ratings", response_model=schemas.RatingOut)
def create_rating(rating: schemas.RatingCreate, db: Session = Depends(get_db)):
    return crud.create_rating(db, rating)

@app.get("/wines/{wine_id}/ratings", response_model=List[schemas.RatingOut])
def get_wine_ratings(wine_id: int, db: Session = Depends(get_db)):
    return crud.get_wine_ratings(db, wine_id)
    
@app.get("/wine")
def get_wine():
    try:
        url = "https://api.grapeminds.eu/public/v1/wines"

        headers = {
            "Authorization": f"Bearer {os.getenv('API_KEY')}"
        }

        response = requests.get(url, headers=headers)

        return {
            "status": response.status_code,
            "data": response.json()
        }

    except Exception as e:
        return {"error": str(e)}

def crc16(data: str):
    crc = 0xFFFF
    for i in range(len(data)):
        crc ^= ord(data[i]) << 8
        for j in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
        crc &= 0xFFFF
    return format(crc, '04X')

def generate_promptpay_payload(phone_or_id: str, amount: float = None):
    def f(id, val):
        return f"{id}{len(val):02d}{val}"

    target = phone_or_id.replace("-", "")
    if len(target) == 10 and target.startswith("0"):
        target = "0066" + target[1:]
    
    account_info = f("00", "A000000677010111")
    if len(target) == 13:
        account_info += f("01", target)
    else:
        account_info += f("02", target)

    payload = f("00", "01")
    payload += f("01", "11")
    payload += f("29", account_info)
    payload += f("53", "764")
    if amount:
        payload += f("54", f"{amount:.2f}")
    payload += f("58", "TH")
    payload += "6304"
    
    crc = crc16(payload)
    return payload + crc

@app.get("/generate-qr")
async def generate_qr(phone: str, amount: float):
    try:
        payload = generate_promptpay_payload(phone, amount)
        
        img = qrcode.make(payload)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Line login endpoints

@app.get("/login/line")
async def login_line(request: Request):
    redirect_uri = request.url_for("auth_line")
    # Fix for Render: Ensure redirect_uri uses https
    if "onrender.com" in str(redirect_uri):
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await oauth.line.authorize_redirect(request, redirect_uri)


@app.get("/auth/line/callback")
async def auth_line(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.line.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LINE OAuth error: {str(e)}")

    # Fetch user profile manually to avoid ID Token verification issues
    resp = await oauth.line.get("v2/profile", token=token)
    profile = resp.json()

    user_id = profile.get("userId")
    name = profile.get("displayName")
    email = f"{user_id}@line-user"

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        user = models.User(
            first_name=name,
            last_name="",
            email=email,
            username=email,
            password=hash_password("line_oauth_no_password"),
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token({
        "user_id": user.id,
        "role": user.role
    })

    return RedirectResponse(url=f"{FRONTEND_URL}?token={jwt_token}")

@app.get("/login/facebook")
async def login_facebook(request: Request):
    redirect_uri = request.url_for("auth_facebook")
    # Fix for Render: Ensure redirect_uri uses https
    if "onrender.com" in str(redirect_uri):
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await oauth.facebook.authorize_redirect(request, redirect_uri)


@app.get("/auth/facebook/callback")
async def auth_facebook(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.facebook.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Facebook OAuth error: {str(e)}")

    resp = await oauth.facebook.get(
        "me?fields=id,name,email",
        token=token
    )
    profile = resp.json()

    email = profile.get("email") or f"{profile.get('id')}@facebook-user"
    name = profile.get("name")

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        user = models.User(
            first_name=name,
            last_name="",
            email=email,
            username=email,
            password=None,
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token({
        "user_id": user.id,
        "role": user.role
    })

    return RedirectResponse(url=f"{FRONTEND_URL}?token={jwt_token}")
