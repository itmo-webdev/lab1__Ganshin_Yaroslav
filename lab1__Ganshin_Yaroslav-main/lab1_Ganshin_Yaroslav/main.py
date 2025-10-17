# main.py (замена целиком)
from fastapi import FastAPI, Depends, HTTPException, Request, status, Header
from fastapi.responses import JSONResponse, Response, RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List, Generator
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from uuid import uuid4
import logging
from sqlalchemy import text 
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

# DB / SQLAlchemy
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, JSON as SAJSON, Text
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.exc import IntegrityError

# auth libs
from argon2 import PasswordHasher, exceptions as argon2_exceptions
from jose import jwt, JWTError
from fastapi_sso.sso.github import GithubSSO
import httpx

# load env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")

JWT_SECRET = os.getenv("JWT_SECRET", "change_me_super_secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://127.0.0.1:8000/auth/github/callback")

# DB setup
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# simple logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# Password hasher
pwd_hasher = PasswordHasher()

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_verified_author = Column(Boolean, default=False, nullable=False)
    avatar = Column(String, nullable=True)

    # new fields:
    password_hash = Column(String, nullable=True)  # nullable for OAuth users
    role = Column(String, default="user", nullable=False)  # 'user' or 'admin'

    news = relationship("News", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    refresh_sessions = relationship("RefreshSession", back_populates="user", cascade="all, delete-orphan")


class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(SAJSON, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    cover = Column(String, nullable=True)

    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    author = relationship("User", back_populates="news")
    comments = relationship("Comment", back_populates="news", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    news_id = Column(Integer, ForeignKey("news.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    news = relationship("News", back_populates="comments")
    author = relationship("User", back_populates="comments")


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="refresh_sessions")


# Pydantic schemas
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
        json_encoders = {datetime: lambda v: v.isoformat()}
        
        
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
        json_encoders = {datetime: lambda v: v.isoformat()}

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
        json_encoders = {datetime: lambda v: v.isoformat()}
        

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        from_attributes = True

# DB dependency
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# utils: password/hash/jwt
def hash_password(plain: str) -> str:
    return pwd_hasher.hash(plain)

def verify_password(hash_: str, plain: str) -> bool:
    try:
        return pwd_hasher.verify(hash_, plain)
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception as e:
        logger.exception("argon2 verify error")
        return False

def create_access_token(user_id: int, role: str, expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = {"sub": str(user_id), "role": role}
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Token invalid or expired")

def create_refresh_session(db: Session, user: User, user_agent: Optional[str]) -> str:
    token = str(uuid4())
    sess = RefreshSession(token=token, user_agent=user_agent, user_id=user.id)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return token

def revoke_refresh_session(db: Session, token: str, user: Optional[User] = None):
    q = db.query(RefreshSession).filter(RefreshSession.token == token)
    if user:
        q = q.filter(RefreshSession.user_id == user.id)
    rs = q.first()
    if rs:
        db.delete(rs)
        db.commit()
        return True
    return False

# current user dependency
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
auth_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = int(payload.get("sub"))
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# role dependency factory
def require_role(min_role: str):
    def _dep(user: User = Depends(get_current_user)):
        # simple role ordering: admin > user
        if min_role == "admin" and user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        return user
    return _dep

# news resolver dependency (протаскивает новость и проверяет право на изменение)
def resolve_news_and_check_editable(news_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    n = db.get(News, news_id)
    if not n:
        raise HTTPException(status_code=404, detail="News not found")
    # разрешено, если автор или админ
    if current_user.role != "admin" and n.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this news")
    return n

# init SSO (GitHub)
github_sso = None
if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    github_sso = GithubSSO(
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        redirect_uri=GITHUB_REDIRECT_URI,
        allow_insecure_http=True,
    )

app = FastAPI(title="Minimal News API with Auth (single-file)")

# --- Глобальная Middleware, закрывающая все ручки, кроме /auth и доков ---
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        path = request.url.path
        # разрешаем открытые пути
        if path.startswith("/auth") or path.startswith("/docs") or path.startswith("/openapi.json") or path.startswith("/redoc") or path.startswith("/static") or path == "/favicon.ico":
            return await call_next(request)


        auth_header = request.headers.get("authorization")
        if not auth_header:
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        # ожидаем "Bearer <token>"
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return JSONResponse({"detail": "Invalid auth scheme"}, status_code=401)
        except Exception:
            return JSONResponse({"detail": "Invalid Authorization header"}, status_code=401)

        # decode token and ensure user exists; attach to request.state
        try:
            payload = decode_access_token(token)
            user_id = int(payload.get("sub"))
            db = SessionLocal()
            user = db.get(User, user_id)
            db.close()
            if not user:
                return JSONResponse({"detail": "User not found"}, status_code=401)
            # attach user to request.state so другие части кода могут использовать если нужно
            request.state.user = user
        except Exception:
            return JSONResponse({"detail": "Token invalid or expired"}, status_code=401)

        return await call_next(request)

# зарегистрировать middleware
app.add_middleware(AuthMiddleware)
# --- конец middleware ---


@app.on_event("startup")
def on_startup():
    # Создаём все таблицы (не изменит существующие столбцы)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # --- Минимальные исправления схемы для совместимости ---
        # Добавляем колонки, если их нет (Postgres поддерживает IF NOT EXISTS для столбцов)
        # password_hash
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR"))
        # role (строка, по умолчанию 'user')
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'user' NOT NULL"))
        # Доп. таблица для refresh-сессий (если её нет)
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS refresh_sessions (
                id SERIAL PRIMARY KEY,
                token VARCHAR UNIQUE NOT NULL,
                user_agent VARCHAR,
                created_at TIMESTAMP DEFAULT now(),
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        db.commit()
        # --- конец исправлений схемы ---

        # теперь безопасно считать пользователей и seed-данные
        user_count = db.query(User).count()
        if user_count == 0:
            a = User(name="Alice", email="alice@example.com", is_verified_author=True, role="admin", password_hash=hash_password("alicepass"))
            b = User(name="Bob", email="bob@example.com", is_verified_author=False, role="user", password_hash=hash_password("bobpass"))
            db.add_all([a, b])
            db.commit()
            db.refresh(a)
            db.refresh(b)
            n = News(title="Первая новость", content={"blocks":[{"type":"p","text":"Hello world"}]}, author_id=a.id)
            db.add(n)
            db.commit()
            db.refresh(n)
            c = Comment(text="Крутая новость!", author_id=b.id, news_id=n.id)
            db.add(c)
            db.commit()
    finally:
        db.close()

# --------------------
# Auth endpoints (email/password)
# --------------------
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

@app.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(data.password)
    user = User(name=data.name, email=data.email, password_hash=hashed, is_verified_author=False)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not create user")
    db.refresh(user)
    return user

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@app.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(user.password_hash, data.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access = create_access_token(user.id, user.role)
    ua = request.headers.get("user-agent", "unknown")
    refresh = create_refresh_session(db, user, ua)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

class RefreshIn(BaseModel):
    refresh_token: str

@app.post("/auth/refresh", response_model=TokenOut)
def refresh_token(data: RefreshIn, request: Request, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "unknown")
    rs = db.query(RefreshSession).filter(RefreshSession.token == data.refresh_token).first()
    if not rs:
        raise HTTPException(status_code=401, detail="Refresh token invalid")
    # rotate: delete old, create new
    user = db.get(User, rs.user_id)
    db.delete(rs)
    db.commit()
    new_refresh = create_refresh_session(db, user, ua)
    access = create_access_token(user.id, user.role)
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}

@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ok = revoke_refresh_session(db, data.refresh_token, current_user)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/auth/sessions", response_model=List[dict])
def list_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(RefreshSession).filter(RefreshSession.user_id == current_user.id).all()
    out = [{"token": s.token, "user_agent": s.user_agent, "created_at": s.created_at} for s in sessions]
    return out

# --------------------
# GitHub OAuth endpoints (fastapi-sso)
# --------------------
@app.get("/auth/github/login")
async def github_login():
    if not github_sso:
        raise HTTPException(status_code=500, detail="GitHub SSO not configured")
    async with github_sso:
        # redirect to GitHub
        return await github_sso.get_login_redirect()

@app.get("/auth/github/callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    print("=== GITHUB CALLBACK HIT ===")
    print("request.url:", request.url)

    try:
        qs = dict(request.query_params)
    except Exception:
        qs = None
    print("query params:", qs)

    if not github_sso:
        raise HTTPException(status_code=500, detail="GitHub SSO not configured")

    async with github_sso:
        profile = await github_sso.verify_and_process(request)

        # --- normalize profile to a plain dict (works for dict, pydantic v1 and v2) ---
        if isinstance(profile, dict):
            prof = profile
        else:
            if hasattr(profile, "model_dump"):
                prof = profile.model_dump()
            elif hasattr(profile, "dict"):
                prof = profile.dict()
            else:
                prof = dict(profile)

        # теперь безопасно читаем поля
        email = prof.get("email") or f"github_{prof.get('id')}@local"
        name = prof.get("name") or prof.get("login") or "github_user"
        avatar = prof.get("avatar_url")

        # Проверяем пользователя в БД
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(name=name, email=email, avatar=avatar, is_verified_author=False)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Создаём токены
        access = create_access_token(user.id, user.role)
        refresh = create_refresh_session(db, user, request.headers.get("user-agent", "unknown"))

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "user": {"id": user.id, "email": user.email, "name": user.name},
        }

# --------------------
# Users endpoints (some kept)
# --------------------
@app.post("/users/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    # if password provided here, we hash it; else leave password_hash None (OAuth)
    data = user_in.dict()
    password = data.pop("password", None) if "password" in data else None
    if password:
        data["password_hash"] = hash_password(password)
    user = User(**data)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not create user")
    db.refresh(user)
    return user

@app.get("/users/{user_id}", response_model=UserOut)
def read_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

@app.get("/users/", response_model=List[UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(User).offset(skip).limit(limit).all()

# --------------------
# News endpoints (create/update/delete with permissions)
# --------------------
@app.post("/news/", response_model=NewsOut, status_code=status.HTTP_201_CREATED)
def create_news(news_in: NewsCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_verified_author:
        raise HTTPException(status_code=403, detail="User is not verified to publish news")
    news = News(author_id=current_user.id, **news_in.dict())
    db.add(news)
    db.commit()
    db.refresh(news)
    return news

@app.get("/news/{news_id}", response_model=NewsOut)
def read_news(news_id: int, db: Session = Depends(get_db)):
    n = db.get(News, news_id)
    if not n:
        raise HTTPException(status_code=404, detail="News not found")
    return n

@app.get("/news/", response_model=List[NewsOut])
def list_news(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(News).offset(skip).limit(limit).all()

@app.put("/news/{news_id}", response_model=NewsOut)
def update_news(news_id: int, news_in: NewsUpdate, news: News = Depends(resolve_news_and_check_editable), db: Session = Depends(get_db)):
    data = news_in.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(news, k, v)
    db.commit()
    db.refresh(news)
    return news

@app.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(news_id: int, news: News = Depends(resolve_news_and_check_editable), db: Session = Depends(get_db)):
    db.delete(news)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --------------------
# Comments endpoints (any user can comment; only author or admin can edit/delete)
# --------------------
@app.post("/comments/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(news_id: int, comment_in: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # current_user гарантирован middleware'ом / зависимостью
    author = db.get(User, current_user.id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    news = db.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    comment = Comment(author_id=author.id, news_id=news_id, **comment_in.dict())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@app.get("/comments/{comment_id}", response_model=CommentOut)
def read_comment(comment_id: int, db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    return c

@app.put("/comments/{comment_id}", response_model=CommentOut)
def update_comment(comment_id: int, comment_in: CommentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    if current_user.role != "admin" and c.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this comment")
    data = comment_in.dict(exclude_unset=True)
    if "text" in data:
        c.text = data["text"]
    db.commit()
    db.refresh(c)
    return c

@app.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    if current_user.role != "admin" and c.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this comment")
    db.delete(c)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
