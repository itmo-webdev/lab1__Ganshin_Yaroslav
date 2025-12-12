from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..models import User, UserRole
from ..schemas import UserCreate, UserOut
from ..dependencies import get_current_user, require_role
from ..security import hash_password
from ..cache import get_json, set_json, delete

USER_CACHE_TTL = 60 * 5

import logging

router = APIRouter(prefix="/users", tags=["users"])

logger = logging.getLogger(__name__)
@router.post("/", response_model=UserOut)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    data = user_in.dict()
    password = data.pop("password", None)
    if password:
        data["password_hash"] = hash_password(password)
    user = User(**data)
    db.add(user)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Could not create user")
    await db.refresh(user)
    await delete(f"user:{user.id}")
    return user

@router.get("/{user_id}", response_model=UserOut)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    cache_key = f"user:{user_id}"
    cached_user = await get_json(cache_key)
    if cached_user:
        logger.info(f"User {user_id} retrieved from cache.")
        return cached_user

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User {user_id} retrieved from DB and cached.")
    await set_json(cache_key, UserOut.from_orm(user).dict(), USER_CACHE_TTL)
    return user

@router.get("/", response_model=List[UserOut])
async def list_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, user_in: UserCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = user_in.dict()
    password = data.pop("password", None)
    for k, v in data.items():
        setattr(user, k, v)
    if password:
        user.password_hash = hash_password(password)
    await db.commit()
    await db.refresh(user)
    await delete(f"user:{user_id}")
    return user

@router.delete("/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    await delete(f"user:{user_id}")
    return {"status": "deleted"}
