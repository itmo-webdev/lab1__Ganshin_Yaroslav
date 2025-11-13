from typing import Optional, Callable, Awaitable
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .db import get_db
from .models import User, News, Comment
from .security import decode_access_token
from .cache import get_json, set_json

auth_scheme = HTTPBearer()
_USER_TTL_SECONDS = 600

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme), db: AsyncSession = Depends(get_db)) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalid or expired")
    user_id = int(payload.get("sub"))

    cached = await get_json(f"user:{user_id}")
    if cached:

        user = User(
            id=cached["id"],
            name=cached["name"],
            email=cached["email"],
            registered_at=cached["registered_at"],
            is_verified_author=cached["is_verified_author"],
            avatar=cached.get("avatar"),
            role=cached["role"],
        )
        return user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    await set_json(
        f"user:{user.id}",
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "registered_at": user.registered_at.isoformat(),
            "is_verified_author": user.is_verified_author,
            "avatar": user.avatar,
            "role": user.role,
        },
        ttl_seconds=_USER_TTL_SECONDS,
    )
    return user

def require_role(min_role: str):
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if min_role == "admin" and user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        return user
    return _dep

async def require_verified_author(user: User = Depends(get_current_user)) -> User:
    if not user.is_verified_author:
        raise HTTPException(status_code=403, detail="User is not verified to publish news")
    return user

async def resolve_news_and_check_editable(news_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> News:
    result = await db.execute(select(News).where(News.id == news_id))
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="News not found")
    if current_user.role != "admin" and n.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this news")
    return n

async def resolve_comment_and_check_owner(comment_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> Comment:
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    if current_user.role != "admin" and c.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return c
