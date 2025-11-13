from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..db import get_db
from ..models import User
from ..schemas import UserOut, RegisterIn, LoginIn, RefreshIn, TokenOut
from ..security import hash_password, verify_password, create_access_token, REFRESH_TOKEN_EXPIRE_MINUTES
from ..dependencies import get_current_user
from ..cache import set_json, get_json, delete as cache_delete, sadd, srem, smembers, mget_json
from datetime import datetime
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])

_RS_TTL = REFRESH_TOKEN_EXPIRE_MINUTES * 60

async def _create_refresh_session(user: User, user_agent: str | None) -> str:
    token = str(uuid.uuid4())
    payload = {"user_id": user.id, "user_agent": user_agent, "created_at": datetime.utcnow().isoformat()}
    await set_json(f"rs:{token}", payload, ttl_seconds=_RS_TTL)
    await sadd(f"rs_user:{user.id}", token)
    return token

async def _revoke_refresh_session(token: str, user: User | None = None) -> bool:
    key = f"rs:{token}"
    rs = await get_json(key)
    if not rs:
        return False
    if user and int(rs.get("user_id", 0)) != int(user.id):
        return False
    await cache_delete(key)
    await srem(f"rs_user:{rs['user_id']}", token)
    return True

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    exists_q = select(User).where(User.email == data.email)
    result = await db.execute(exists_q)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(data.password)
    user = User(name=data.name, email=data.email, password_hash=hashed, is_verified_author=False)
    db.add(user)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Could not create user")
    await db.refresh(user)
    return user

@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(user.password_hash, data.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access = create_access_token(user.id, user.role)
    ua = request.headers.get("user-agent", "unknown")
    refresh = await _create_refresh_session(user, ua)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

@router.post("/refresh", response_model=TokenOut)
async def refresh_token(data: RefreshIn, request: Request, db: AsyncSession = Depends(get_db)):
    rs = await get_json(f"rs:{data.refresh_token}")
    if not rs:
        raise HTTPException(status_code=400, detail="Refresh token invalid")
    user = await db.get(User, int(rs["user_id"]))
    # revoke old
    await _revoke_refresh_session(data.refresh_token)
    # issue new
    new_refresh = await _create_refresh_session(user, request.headers.get("user-agent", "unknown"))
    access = create_access_token(user.id, user.role)
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshIn, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ok = await _revoke_refresh_session(data.refresh_token, current_user)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/sessions", response_model=List[dict])
async def list_sessions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    tokens = await smembers(f"rs_user:{current_user.id}")
    keys = [f"rs:{t}" for t in tokens]
    items = await mget_json(keys) if keys else []
    out: List[dict] = []
    for t, meta in zip(tokens, items):
        if not meta:
            continue
        out.append({"token": t, "user_agent": meta.get("user_agent"), "created_at": meta.get("created_at")})
    return out
