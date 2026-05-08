from jose import JWTError, jwt
from core.security import SECRET_KEY, ALGORITHM

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
