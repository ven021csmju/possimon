from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import os
import secrets
import json
import base64
from auth.dependencies import get_db, get_current_user
from core.security import verify_password, create_access_token, hash_password
from core.config import settings
from auth.oauth import oauth
import models
import schemas

router = APIRouter(tags=["auth"])

def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600
    )

@router.post("/login")
@router.post("/login/pos")
def login_pos(request: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    # Allow login by username OR email
    user = db.query(models.User).filter(
        (models.User.username == request.username) | (models.User.email == request.username)
    ).first()

    if not user or not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "user_id": user.id,
        "role": user.role
    })
    
    set_auth_cookie(response, token)

    return {"access_token": token, "message": "Login success"}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=schemas.UserOut)
def get_me(user: models.User = Depends(get_current_user)):
    return user

# --- Multi-Frontend Google OAuth ---

@router.get("/login/google/web")
async def login_google_web(request: Request):
    callback_url = request.url_for("auth_google")
    if "onrender.com" in str(callback_url):
        callback_url = str(callback_url).replace("http://", "https://")
    
    # Use state to pass the source
    state_data = {"source": "web"}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    return await oauth.google.authorize_redirect(request, str(callback_url), state=state)

@router.get("/login/google/pos")
async def login_google_pos(request: Request):
    callback_url = request.url_for("auth_google")
    if "onrender.com" in str(callback_url):
        callback_url = str(callback_url).replace("http://", "https://")
    
    state_data = {"source": "pos"}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    return await oauth.google.authorize_redirect(request, str(callback_url), state=state)

@router.get("/google/callback", name="auth_google")
async def auth_google(request: Request, db: Session = Depends(get_db)):
    try:
        # Authlib verifies the state internally for security (CSRF)
        # We also manually extract our source from the state
        state_str = request.query_params.get("state")
        source = "web" # default
        if state_str:
            try:
                # Authlib might append its own stuff to state or it might be just what we sent
                # If we use Authlib's built-in state management, it might be tricky.
                # Let's try to parse it.
                decoded_state = json.loads(base64.urlsafe_b64decode(state_str).decode())
                source = decoded_state.get("source", "web")
            except:
                pass

        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

    resp = await oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo', token=token)
    user_info = resp.json()
    email = user_info.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Default role based on source or just 'customer'
        role = "customer"
        if source == "pos":
            # Potentially check if this email is allowed to be an employee
            # For now, keep it customer or handle specifically
            pass

        user = models.User(
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            email=email,
            username=email,
            password=hash_password(secrets.token_hex(32)),
            role=role,
            is_social=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token({"user_id": user.id, "role": user.role})
    
    # Determine redirect URL based on source
    if source == "pos":
        redirect_url = settings.POS_FRONTEND_URL
    else:
        redirect_url = settings.WEB_FRONTEND_URL
        
    response = RedirectResponse(url=redirect_url)
    set_auth_cookie(response, jwt_token)
    return response

# --- Multi-Frontend LINE OAuth ---

@router.get("/login/line/web")
async def login_line_web(request: Request):
    callback_url = request.url_for("auth_line")
    if "onrender.com" in str(callback_url):
        callback_url = str(callback_url).replace("http://", "https://")
    
    state_data = {"source": "web"}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    return await oauth.line.authorize_redirect(request, str(callback_url), state=state)

@router.get("/login/line/pos")
async def login_line_pos(request: Request):
    callback_url = request.url_for("auth_line")
    if "onrender.com" in str(callback_url):
        callback_url = str(callback_url).replace("http://", "https://")
    
    state_data = {"source": "pos"}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    return await oauth.line.authorize_redirect(request, str(callback_url), state=state)

@router.get("/line/callback", name="auth_line")
async def auth_line(request: Request, db: Session = Depends(get_db)):
    try:
        # Retrieve state for frontend source
        state_str = request.query_params.get("state")
        source = "web"
        if state_str:
            try:
                decoded_state = json.loads(base64.urlsafe_b64decode(state_str).decode())
                source = decoded_state.get("source", "web")
            except:
                pass

        token = await oauth.line.authorize_access_token(request)
        
        # Parse and verify ID Token using RS256 and registered JWKS
        user_info = await oauth.line.parse_id_token(request, token)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LINE OAuth error: {str(e)}")

    user_id = user_info.get("sub")
    name = user_info.get("name")
    email = user_info.get("email")

    if not email:
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
    
    redirect_url = settings.POS_FRONTEND_URL if source == "pos" else settings.WEB_FRONTEND_URL
        
    response = RedirectResponse(url=redirect_url)
    set_auth_cookie(response, jwt_token)
    return response

# --- Generic OAuth Login (Old, kept for compatibility if needed) ---

@router.get("/login/google")
async def login_google(request: Request):
    callback_url = request.url_for("auth_google")
    if "onrender.com" in str(callback_url):
        callback_url = str(callback_url).replace("http://", "https://")
    return await oauth.google.authorize_redirect(request, str(callback_url))

@router.get("/login/line")
async def login_line(request: Request):
    callback_url = request.url_for("auth_line")
    if "onrender.com" in str(callback_url):
        callback_url = str(callback_url).replace("http://", "https://")
    return await oauth.line.authorize_redirect(request, str(callback_url))

@router.get("/login/facebook")
async def login_facebook(request: Request):
    redirect_uri = request.url_for("auth_facebook")
    if "onrender.com" in str(redirect_uri):
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await oauth.facebook.authorize_redirect(request, redirect_uri)

@router.get("/facebook/callback", name="auth_facebook")
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
    response = RedirectResponse(url=settings.WEB_FRONTEND_URL)
    set_auth_cookie(response, jwt_token)
    return response

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
