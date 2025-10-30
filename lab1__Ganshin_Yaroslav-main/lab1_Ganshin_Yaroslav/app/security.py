import os
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from argon2 import PasswordHasher, exceptions as argon2_exceptions
from jose import jwt, JWTError

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "change_me_super_secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

pwd_hasher = PasswordHasher()

def hash_password(plain: str) -> str:
    return pwd_hasher.hash(plain)

def verify_password(hash_: str, plain: str) -> bool:
    try:
        return pwd_hasher.verify(hash_, plain)
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception:
        return False

def create_access_token(user_id: int, role: str, expire_minutes: int | None = None) -> str:
    if expire_minutes is None:
        expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = {"sub": str(user_id), "role": role}
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded

def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload
