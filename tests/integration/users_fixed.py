
"""
Users router - register, login, get profile, update, delete
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging


from email_validator import validate_email, EmailNotValidError

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.security import get_password_hash, verify_password
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register new user with email validation.
    Валидирует email перед сохранением в Базу данных
    Обрабатывает IntegrityError.Т.Е. ДУБЛИКАТЫ
    Возвращает 422 для невалидного email, 409 для дубликата
    """
    try:
        # STEP 1: VALIDATE EMAIL FORMAT
        try:
            validate_email(user_data.email)
        except EmailNotValidError as e:
            logger.warning(f"Invalid email format: {user_data.email}")
            raise HTTPException(
                status_code=422,
                detail=f"Invalid email format: {str(e)}"
            )
        
        # STEP 2: CHECK IF USER ALREADY EXISTS
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            logger.warning(f"Email already registered: {user_data.email}")
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )
        
        # STEP 3: CREATE USER WITH HASHED PASSWORD
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            password_hash=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User registered successfully: {user_data.email}")
        return db_user
        
    except HTTPException:
        # HTTP exceptions (422, 409, etc.)
        raise
    
    except IntegrityError as e:
        # Database constraint violation (should not happen after email validation)
        db.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Database constraint violation"
        )
    
    except Exception as e:
        # Unexpected error
        db.rollback()
        logger.error(f"Unexpected error during registration: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/login")
async def login(credentials: dict, db: Session = Depends(get_db)):
    """вход с логином и паролем (placeholder)."""
    user = db.query(User).filter(User.email == credentials.get("email")).first()
    if not user or not verify_password(credentials.get("password"), user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": "token_here", "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """профиль текущего пользователя."""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """ ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить пользователя."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for key, value in user_data.items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user (only owner can delete)."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return None
