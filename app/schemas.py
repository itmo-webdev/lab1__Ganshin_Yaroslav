from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: Optional[str] = None
    is_verified_author: Optional[bool] = False
    avatar: Optional[str] = None

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    registered_at: datetime
    is_verified_author: bool
    avatar: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class NewsCreate(BaseModel):
    title: str
    content: Any
    cover: Optional[str] = None

    class Config:
        from_attributes = True

class NewsUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[Any] = None
    cover: Optional[str] = None

    class Config:
        from_attributes = True

class NewsOut(BaseModel):
    id: int
    title: str
    content: Any
    published_at: datetime
    cover: Optional[str]
    author: UserOut

    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    text: str

    class Config:
        from_attributes = True

class CommentUpdate(BaseModel):
    text: Optional[str] = None

    class Config:
        from_attributes = True

class CommentOut(BaseModel):
    id: int
    text: str
    published_at: datetime
    author: UserOut

    class Config:
        from_attributes = True

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        from_attributes = True

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class RefreshIn(BaseModel):
    refresh_token: str
