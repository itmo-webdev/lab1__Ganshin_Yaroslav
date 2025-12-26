
"""

Тестирование Dependency  for FastAPI

"""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta
from typing import Optional

from app.db import get_db
from app.models import User
from app.config import settings

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Constants
SECRET_KEY = settings.SECRET_KEY or "your-secret-key-change-in-production"
ALGORITHM = settings.ALGORITHM or "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES or 30


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Проверяет длину токена (не более 1000 символов)
    Обрабатывает все типы JWT ошибок
    Логирует неожиданные ошибки для отладки
    Возвращает 401 для любой ошибки аутентификации
    """
    token = credentials.credentials if hasattr(credentials, 'credentials') else str(credentials)
    
    try:
        # STEP 1:Валидация длинны токекна
        # JWT tokens обычно < 1000 символов. Если больше - это попытка DoS
        if len(token) > 1000:
            logger.warning(f"Token too long: {len(token)} characters")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format (too long)",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # STEP 2: DECODE AND VALIDATE TOKEN
        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            logger.info(f"Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidSignatureError:
            logger.warning(f"Invalid token signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {type(e).__name__}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # STEP 3: EXTRACT EMAIL FROM PAYLOAD
        email = payload.get("sub")
        if email is None:
            logger.warning(f"Token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # STEP 4: GET USER FROM DATABASE
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            logger.warning(f"User not found: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        logger.debug(f"User authenticated: {email}")
        return user
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        # Unexpected error - log it for debugging
        logger.error(
            f"Unexpected error during token validation: "
            f"{type(e).__name__}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """берем если аутентифицирован."""
    if credentials is None:
        return None
    
    return await get_current_user(credentials, db)
