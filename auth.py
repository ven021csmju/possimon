from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from authlib.integrations.starlette_client import OAuth
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_only")
ALGORITHM = "HS256"

# Switch to pbkdf2_sha256 which is robust and doesn't have the 72-byte limit
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

oauth.register(
    name='line',
    client_id=os.getenv("LINE_CHANNEL_ID"),
    client_secret=os.getenv("LINE_CHANNEL_SECRET"),
    access_token_url='https://api.line.me/oauth2/v2.1/token',
    authorize_url='https://access.line.me/oauth2/v2.1/authorize',
    api_base_url='https://api.line.me/',
    client_kwargs={
        'scope': 'profile', # Remove 'openid' to bypass ID Token verification issues
        'token_endpoint_auth_method': 'client_secret_post',
    }
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
