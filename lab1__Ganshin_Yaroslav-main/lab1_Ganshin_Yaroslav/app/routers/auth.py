from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..db import get_db
from ..models import User, RefreshSession
from ..schemas import UserOut, RegisterIn, LoginIn, RefreshIn, TokenOut
from ..security import hash_password, verify_password, create_access_token
from ..dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

async def _create_refresh_session(db: AsyncSession, user: User, user_agent: str | None) -> str:
    import uuid
    token = str(uuid.uuid4())
    rs = RefreshSession(token=token, user_agent=user_agent, user_id=user.id)
    db.add(rs)
    await db.commit()
    await db.refresh(rs)
    return token

async def _revoke_refresh_session(db: AsyncSession, token: str, user: User | None = None) -> bool:
    q = select(RefreshSession).where(RefreshSession.token == token)
    if user:
        q = q.where(RefreshSession.user_id == user.id)
    result = await db.execute(q)
    rs = result.scalar_one_or_none()
    if rs:
        await db.delete(rs)
        await db.commit()
        return True
    return False

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
    refresh = await _create_refresh_session(db, user, ua)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

@router.post("/refresh", response_model=TokenOut)
async def refresh_token(data: RefreshIn, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshSession).where(RefreshSession.token == data.refresh_token))
    rs = result.scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=400, detail="Refresh token invalid")
    user = await db.get(User, rs.user_id)
    await db.delete(rs)
    await db.commit()
    new_refresh = await _create_refresh_session(db, user, request.headers.get("user-agent", "unknown"))
    access = create_access_token(user.id, user.role)
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshIn, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ok = await _revoke_refresh_session(db, data.refresh_token, current_user)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/sessions", response_model=List[dict])
async def list_sessions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshSession).where(RefreshSession.user_id == current_user.id))
    sessions = result.scalars().all()
    out = [{"token": s.token, "user_agent": s.user_agent, "created_at": s.created_at} for s in sessions]
    return out
