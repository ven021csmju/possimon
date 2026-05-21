from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from typing import Optional
from core.config import settings
from core.logging_config import logger

def create_access_token(data: dict):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access"
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh"
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str, expected_type: Optional[str] = None):
    try:
        # Add 60 seconds of leeway for iat, nbf, and exp to handle clock drift
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"leeway": 60}
        )
        
        if expected_type and payload.get("type") != expected_type:
            logger.warning(f"Token type mismatch: expected {expected_type}, got {payload.get('type')}")
            return None
            
        return payload
    except JWTError as e:
        # Log as warning so it shows up in production (Level INFO and above)
        logger.warning(f"JWT Decode error: {str(e)} | Token prefix: {token[:15]}...")
        return None
