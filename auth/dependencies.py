from fastapi import Depends, status, Request
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from auth.jwt import decode_token
from core.config import settings
from exceptions.auth_exception import AuthException

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    # 1. Prioritize Authorization header (Bearer token)
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        token_source = "header"
    
    # 2. Fallback to Cookie if header is missing
    if not token:
        token = request.cookies.get(settings.COOKIE_NAME)
        token_source = "cookie"

    if not token:
        raise AuthException(
            message="Not authenticated",
            code="NOT_AUTHENTICATED"
        )
    
    payload = decode_token(token, expected_type="access")
    if not payload:
        logger.warning(f"Failed to decode access token from {token_source}")
        raise AuthException(
            message="Invalid or expired access token",
            code="INVALID_TOKEN"
        )
    
    user_id = payload.get("sub") or payload.get("user_id") # Support both sub and old user_id for migration
    if user_id is None:
        raise AuthException(
            message="Invalid token payload",
            code="INVALID_TOKEN_PAYLOAD"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise AuthException(
            message="User not found",
            code="USER_NOT_FOUND"
        )
    return user

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: models.User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise AuthException(
                message="You do not have enough permissions",
                code="PERMISSION_DENIED",
                status_code=status.HTTP_403_FORBIDDEN
            )
        return user
