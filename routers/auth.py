from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import os
import secrets
from auth.dependencies import get_db
from core.security import verify_password, create_access_token, hash_password
from auth.oauth import oauth
import models
import schemas

router = APIRouter(tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000/auth/success")

@router.post("/login")
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == request.username).first()

    if not user or not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "user_id": user.id,
        "role": user.role
    })

    return {"access_token": token}

@router.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()

    if existing_user:
        existing_user.first_name = user.first_name
        existing_user.last_name = user.last_name
        existing_user.phone = user.phone
        existing_user.password = hash_password(user.password)
        existing_user.is_social = False
        db.commit()
        db.refresh(existing_user)
        return {"message": "user updated successfully", "user_id": existing_user.id}

    existing_username = db.query(models.User).filter(models.User.username == user.username).first()
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
            role="customer",
            is_social=False
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "register success", "user_id": new_user.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/login/google")
async def login_google(request: Request):
    # Use request.url_for to get the internal route URL
    callback_url = request.url_for("auth_google")
    
    # Render Force HTTPS logic
    if "onrender.com" in str(callback_url):
        callback_url = str(callback_url).replace("http://", "https://")
    
    return await oauth.google.authorize_redirect(request, str(callback_url))

@router.get("/google/callback", name="auth_google")
async def auth_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        # Logging error would be better here
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

    resp = await oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo', token=token)
    user_info = resp.json()
    email = user_info.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            email=email,
            username=email,
            password=hash_password(secrets.token_hex(32)),
            role="customer",
            is_social=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token({"user_id": user.id, "role": user.role})
    
    # Redirect to frontend with token
    return RedirectResponse(url=f"{FRONTEND_URL}?token={jwt_token}")

@router.get("/login/line")
async def login_line(request: Request):
    redirect_uri = request.url_for("auth_line")

    if "onrender.com" in str(redirect_uri):
        redirect_uri = str(redirect_uri).replace("http://", "https://")

    print("LINE REDIRECT URI =", redirect_uri)

    return await oauth.line.authorize_redirect(
        request,
        redirect_uri
    )

@router.get("/line/callback")
async def auth_line(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.line.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LINE OAuth error: {str(e)}")

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
            password=hash_password(secrets.token_hex(32)),
            role="customer",
            is_social=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token({"user_id": user.id, "role": user.role})
    return RedirectResponse(url=f"{FRONTEND_URL}?token={jwt_token}")

@router.get("/login/facebook")
async def login_facebook(request: Request):
    redirect_uri = request.url_for("auth_facebook")
    if "onrender.com" in str(redirect_uri):
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await oauth.facebook.authorize_redirect(request, redirect_uri)

@router.get("/facebook/callback")
async def auth_facebook(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.facebook.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Facebook OAuth error: {str(e)}")

    resp = await oauth.facebook.get("me?fields=id,name,email", token=token)
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
            password=hash_password(secrets.token_hex(32)),
            role="customer",
            is_social=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token({"user_id": user.id, "role": user.role})
    return RedirectResponse(url=f"{FRONTEND_URL}?token={jwt_token}")
