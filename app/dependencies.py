from typing import Optional, Callable, Awaitable, TypeVar, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .db import get_db
from .models import User, News, Comment, UserRole
from .security import decode_access_token
from .cache import get_json, set_json

auth_scheme = HTTPBearer()
_USER_TTL_SECONDS = 600

class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

T = TypeVar('T')

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme), db: AsyncSession = Depends(get_db)) -> User:
    if not credentials:
        raise UnauthorizedException("Not authenticated")
        
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        if not payload:
            raise UnauthorizedException("Invalid token")
            
        user_id = int(payload.get("sub"))
        if not user_id:
            raise UnauthorizedException("Invalid token payload")
            
        # Cпроверим кеш
        cached = await get_json(f"user:{user_id}")
        if cached:
            return User(
                id=cached["id"],
                name=cached["name"],
                email=cached["email"],
                registered_at=cached["registered_at"],
                is_verified_author=cached["is_verified_author"],
                avatar=cached.get("avatar"),
                role=cached["role"],
            )
            
        # если не в кеше
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise UnauthorizedException("User not found")

        # кеш
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
            ttl_seconds=_USER_TTL_SECONDS
        )
        return user
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise UnauthorizedException("Invalid authentication credentials")

def require_role(required_role: UserRole) -> Callable[[User], Awaitable[User]]:
    """
    Dependency to check if user has required role.
    Raises 403 Forbidden if user doesn't have required role.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role < required_role:
            raise ForbiddenException(
                f"Requires {required_role.name} role or higher. Current role: {current_user.role.name}"
            )
        return current_user
    return role_checker

# роли
require_admin = require_role(UserRole.ADMIN)
require_moderator = require_role(UserRole.MODERATOR)
require_author = require_role(UserRole.AUTHOR)
require_user = require_role(UserRole.USER)

async def require_verified_author(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to check if user is a verified author.
    Raises 403 Forbidden if user is not a verified author.
    """
    if not current_user.is_verified_author:
        raise ForbiddenException("User is not a verified author")
    return current_user

async def resolve_news_and_check_editable(news_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> News:
    """
    Resolve news by ID and check if current user can edit it.
    Raises 404 if news not found, 403 if user can't edit it.
    """
    result = await db.execute(
        select(News)
        .options(selectinload(News.author))
        .where(News.id == news_id)
    )
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    
    # админ
    if current_user.role == UserRole.ADMIN:
        return news
        
    # автор
    if news.author_id == current_user.id:
        return news
        
    # модер
    if current_user.role == UserRole.MODERATOR:
        return news
        
    raise ForbiddenException("You don't have permission to edit this news")

async def resolve_comment_and_check_owner(comment_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> Comment:
    """
    Resolve comment by ID and check if current user is the owner.
    Raises 404 if comment not found, 403 if user is not the owner.
    """
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # админ
    if current_user.role == UserRole.ADMIN:
        return comment
        
    # автор
    if comment.author_id == current_user.id:
        return comment
        
    # модер
    if current_user.role == UserRole.MODERATOR:
        return comment
        
    raise ForbiddenException("You don't have permission to edit this comment")
