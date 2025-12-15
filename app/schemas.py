from datetime import datetime
import re
from pydantic import BaseModel, EmailStr, Field, field_validator
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
    email: EmailStr = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", v):
            raise ValueError('Password must contain at least one special character')
        return v

class LoginIn(BaseModel):
    email: EmailStr = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", v):
            raise ValueError('Password must contain at least one special character')
        return v

class RefreshIn(BaseModel):
    refresh_token: str