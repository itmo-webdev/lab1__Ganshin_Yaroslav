import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi_sso.sso.github import GithubSSO

from ..db import get_db
from ..models import User, RefreshSession
from ..security import create_access_token

router = APIRouter(prefix="/auth/github", tags=["auth", "oauth"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://127.0.0.1:8000/auth/github/callback")

github_sso = None
if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    github_sso = GithubSSO(
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        redirect_uri=GITHUB_REDIRECT_URI,
        allow_insecure_http=True,
    )

async def _create_refresh_session(db: AsyncSession, user: User, user_agent: str | None) -> str:
    import uuid
    token = str(uuid.uuid4())
    rs = RefreshSession(token=token, user_agent=user_agent, user_id=user.id)
    db.add(rs)
    await db.commit()
    await db.refresh(rs)
    return token

@router.get("/login")
async def github_login():
    if not github_sso:
        raise HTTPException(status_code=500, detail="GitHub SSO not configured")
    async with github_sso:
        return await github_sso.get_login_redirect()

@router.get("/callback")
async def github_callback(request: Request, db: AsyncSession = Depends(get_db)):
    if not github_sso:
        raise HTTPException(status_code=500, detail="GitHub SSO not configured")
    async with github_sso:
        profile = await github_sso.verify_and_process(request)

        if isinstance(profile, dict):
            prof = profile
        else:
            if hasattr(profile, "model_dump"):
                prof = profile.model_dump()
            elif hasattr(profile, "dict"):
                prof = profile.dict()
            else:
                prof = dict(profile)

        email = prof.get("email") or f"github_{prof.get('id')}@local"
        name = prof.get("name") or prof.get("login") or "github_user"
        avatar = prof.get("avatar_url")

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(name=name, email=email, avatar=avatar, is_verified_author=False)
            db.add(user)
            await db.commit()
            await db.refresh(user)

        access = create_access_token(user.id, user.role)
        refresh = await _create_refresh_session(db, user, request.headers.get("user-agent", "unknown"))

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "user": {"id": user.id, "email": user.email, "name": user.name},
        }
