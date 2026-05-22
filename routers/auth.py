from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import secrets
import json
import base64
import httpx
from authlib.integrations.base_client.errors import OAuthError
from auth.dependencies import get_db, get_current_user
from core.security import verify_password, hash_password
from core.config import settings
from auth.jwt import create_access_token, create_refresh_token, decode_token
from auth.oauth import oauth
import models
import schemas
from exceptions.auth_exception import AuthException
from services import notification_service

router = APIRouter(tags=["auth"])

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    # Access Token Cookie
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    # Refresh Token Cookie
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    )

@router.post("/login")
@router.post("/login/pos")
def login_pos(request: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    # Allow login by username OR email
    user = db.query(models.User).filter(
        (models.User.username == request.username) | (models.User.email == request.username)
    ).first()

    if not user or not verify_password(request.password, user.password):
        raise AuthException(message="Invalid credentials", code="INVALID_CREDENTIALS")

    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "message": "Login success",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
    }

@router.post("/refresh")
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    
    if not refresh_token:
        raise AuthException(message="Refresh token missing", code="REFRESH_TOKEN_MISSING")

    payload = decode_token(refresh_token, expected_type="refresh")
    if not payload:
        raise AuthException(message="Invalid or expired refresh token", code="INVALID_REFRESH_TOKEN")

    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise AuthException(message="User not found", code="USER_NOT_FOUND")

    token_data = {"sub": str(user.id), "role": user.role}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    set_auth_cookies(response, new_access_token, new_refresh_token)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "message": "Token refreshed"
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
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

@router.get("/google") # Alias for /api/auth/google
@router.get("/login/google")
async def login_google(request: Request, source: str = "web", redirect_url: Optional[str] = None):
    callback_url = request.url_for("auth_google")
    # Force HTTPS for callback on Render
    if "onrender.com" in str(callback_url) or settings.ENV == "production":
        callback_url = str(callback_url).replace("http://", "https://")
    
    # Auto-detect redirect_url if not provided
    if not redirect_url:
        referer = request.headers.get("referer")
        if referer:
            # Use the referer domain but append /auth/success
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            redirect_url = f"{parsed.scheme}://{parsed.netloc}/auth/success"
        else:
            redirect_url = settings.POS_FRONTEND_URL if source == "pos" else settings.WEB_FRONTEND_URL

    # Pass source and dynamic redirect_url in state
    state_data = {"source": source, "redirect_url": redirect_url}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    return await oauth.google.authorize_redirect(request, str(callback_url), state=state)

@router.get("/login/google/web")
async def login_google_web(request: Request):
    return await login_google(request, source="web")

@router.get("/login/google/pos")
async def login_google_pos(request: Request):
    return await login_google(request, source="pos")

def get_or_create_oauth_user(db: Session, provider: str, provider_id: str, email: Optional[str], name: str):
    user = db.query(models.User).filter(
        models.User.provider == provider,
        models.User.provider_id == provider_id
    ).first()
    created = False

    if not user:
        if email:
            user = db.query(models.User).filter(models.User.email == email).first()

        if not user:
            username = f"{provider}_{provider_id}"
            user = models.User(
                provider=provider,
                provider_id=provider_id,
                email=email,
                username=username,
                first_name=name,
                last_name="",
                role="customer"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created = True
        else:
            user.provider = provider
            user.provider_id = provider_id
            if name and not user.first_name:
                user.first_name = name
            if user.last_name is None:
                user.last_name = ""
            db.commit()
            db.refresh(user)
    return user, created

async def fetch_line_access_token(request: Request):
    error = request.query_params.get("error")
    if error:
        description = request.query_params.get("error_description")
        raise OAuthError(error=error, description=description)

    params = {
        "code": request.query_params.get("code"),
        "state": request.query_params.get("state"),
    }
    state_data = await oauth.line.framework.get_state_data(request.session, params.get("state"))
    await oauth.line.framework.clear_state_data(request.session, params.get("state"))
    params = oauth.line._format_state_params(state_data, params)
    token = await oauth.line.fetch_access_token(**params)
    return token, state_data

async def verify_line_id_token(id_token: str, nonce: Optional[str] = None):
    data = {
        "id_token": id_token,
        "client_id": settings.LINE_CHANNEL_ID,
    }
    if nonce:
        data["nonce"] = nonce

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.line.me/oauth2/v2.1/verify",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise AuthException(message=f"LINE ID token verification failed: {detail}", code="LINE_ID_TOKEN_INVALID")

    return response.json()

@router.get("/line/callback", name="auth_line")
async def auth_line(request: Request, db: Session = Depends(get_db)):
    try:
        # Retrieve state for frontend source and dynamic redirect
        state_str = request.query_params.get("state")
        source = "web"
        redirect_base = None
        if state_str:
            try:
                decoded_state = json.loads(base64.urlsafe_b64decode(state_str).decode())
                source = decoded_state.get("source", "web")
                redirect_base = decoded_state.get("redirect_url")
            except:
                pass

        if not redirect_base:
            redirect_base = settings.POS_FRONTEND_URL if source == "pos" else settings.WEB_FRONTEND_URL

        token, state_data = await fetch_line_access_token(request)
        id_token = token.get("id_token")
        if not id_token:
            raise AuthException(message="LINE did not return an ID token", code="LINE_ID_TOKEN_MISSING")

        user_info = await verify_line_id_token(id_token, state_data.get("nonce"))
        
        user, created = get_or_create_oauth_user(
            db, "line", user_info.get("sub"), user_info.get("email"), user_info.get("name", "Line User")
        )
        if created:
            await notification_service.notify_new_customer(user)

        # Role Validation for POS
        if source == "pos" and user.role not in settings.POS_ALLOWED_ROLES:
            return RedirectResponse(url=f"{redirect_base}?error=unauthorized_role")

        token_data = {"sub": str(user.id), "role": user.role}
        jwt_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        redirect_url = f"{redirect_base}?token={jwt_token}"
            
        response = RedirectResponse(url=redirect_url)
        set_auth_cookies(response, jwt_token, refresh_token)
        return response
    except Exception as e:
        raise AuthException(message=f"LINE OAuth error: {str(e)}", code="LINE_OAUTH_ERROR")

@router.get("/google/callback", name="auth_google")
async def auth_google(request: Request, db: Session = Depends(get_db)):
    try:
        # Authlib verifies the state internally for security (CSRF)
        state_str = request.query_params.get("state")
        source = "web"
        redirect_base = None
        if state_str:
            try:
                decoded_state = json.loads(base64.urlsafe_b64decode(state_str).decode())
                source = decoded_state.get("source", "web")
                redirect_base = decoded_state.get("redirect_url")
            except:
                pass

        if not redirect_base:
            redirect_base = settings.POS_FRONTEND_URL if source == "pos" else settings.WEB_FRONTEND_URL

        token = await oauth.google.authorize_access_token(request)
        resp = await oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo', token=token)
        user_info = resp.json()
        
        user, created = get_or_create_oauth_user(
            db, "google", user_info.get("id"), user_info.get("email"), user_info.get("name")
        )
        if created:
            await notification_service.notify_new_customer(user)

        # Role Validation for POS
        if source == "pos" and user.role not in settings.POS_ALLOWED_ROLES:
            return RedirectResponse(url=f"{redirect_base}?error=unauthorized_role")

        token_data = {"sub": str(user.id), "role": user.role}
        jwt_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Determine redirect URL based on state and append token
        redirect_url = f"{redirect_base}?token={jwt_token}"
            
        response = RedirectResponse(url=redirect_url)
        set_auth_cookies(response, jwt_token, refresh_token)
        return response
    except Exception as e:
        raise AuthException(message=f"Google OAuth error: {str(e)}", code="GOOGLE_OAUTH_ERROR")

# --- Generic OAuth Login ---

@router.get("/line")
@router.get("/login/line")
async def login_line(request: Request, source: str = "web", redirect_url: Optional[str] = None):
    callback_url = request.url_for("auth_line")
    if "onrender.com" in str(callback_url) or settings.ENV == "production":
        callback_url = str(callback_url).replace("http://", "https://")
    
    # Auto-detect redirect_url if not provided
    if not redirect_url:
        referer = request.headers.get("referer")
        if referer:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            redirect_url = f"{parsed.scheme}://{parsed.netloc}/auth/success"
        else:
            redirect_url = settings.POS_FRONTEND_URL if source == "pos" else settings.WEB_FRONTEND_URL

    # Pass source and dynamic redirect_url in state
    state_data = {"source": source, "redirect_url": redirect_url}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    return await oauth.line.authorize_redirect(request, str(callback_url), state=state)

@router.get("/login/line/web")
async def login_line_web(request: Request):
    return await login_line(request, source="web")

@router.get("/login/line/pos")
async def login_line_pos(request: Request):
    return await login_line(request, source="pos")

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
        raise AuthException(message=f"Facebook OAuth error: {str(e)}", code="FACEBOOK_OAUTH_ERROR")

    resp = await oauth.facebook.get("me?fields=id,name,email", token=token)
    profile = resp.json()
    email = profile.get("email") or f"{profile.get('id')}@facebook-user"
    name = profile.get("name")

    user = db.query(models.User).filter(models.User.email == email).first()
    created = False
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
        created = True

    if created:
        await notification_service.notify_new_customer(user)

    token_data = {"sub": str(user.id), "role": user.role}
    jwt_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    response = RedirectResponse(url=settings.WEB_FRONTEND_URL)
    set_auth_cookies(response, jwt_token, refresh_token)
    return response

@router.post("/register")
def register(
    user: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
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
        raise AuthException(message="Username already exists", code="USERNAME_EXISTS")

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
        background_tasks.add_task(notification_service.notify_new_customer, new_user)
        return {"message": "register success", "user_id": new_user.id}
    except Exception as e:
        db.rollback()
        raise AuthException(message=str(e), status_code=500, code="REGISTRATION_ERROR")
