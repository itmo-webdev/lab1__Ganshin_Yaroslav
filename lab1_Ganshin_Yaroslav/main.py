
from fastapi.responses import JSONResponse, Response
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List, Generator
from datetime import datetime
import os
from dotenv import load_dotenv


from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, JSON as SAJSON
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.exc import IntegrityError


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_verified_author = Column(Boolean, default=False, nullable=False)
    avatar = Column(String, nullable=True)

    news = relationship("News", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")

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
    text = Column(String, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    news_id = Column(Integer, ForeignKey("news.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    news = relationship("News", back_populates="comments")
    author = relationship("User", back_populates="comments")


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    is_verified_author: Optional[bool] = False
    avatar: Optional[str] = None

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    registered_at: datetime
    is_verified_author: bool
    avatar: Optional[str] = None
    class Config:
        orm_mode = True

class NewsCreate(BaseModel):
    title: str
    content: Any  
    cover: Optional[str] = None

class NewsUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[Any] = None
    cover: Optional[str] = None

class NewsOut(BaseModel):
    id: int
    title: str
    content: Any
    published_at: datetime
    cover: Optional[str]
    author: UserOut
    class Config:
        orm_mode = True

class CommentCreate(BaseModel):
    text: str

class CommentUpdate(BaseModel):
    text: Optional[str] = None

class CommentOut(BaseModel):
    id: int
    text: str
    published_at: datetime
    author: UserOut
    class Config:
        orm_mode = True


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="Minimal News API (single-file)")


@app.on_event("startup")
def on_startup():
    
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            a = User(name="Alice", email="alice@example.com", is_verified_author=True)
            b = User(name="Bob", email="bob@example.com", is_verified_author=False)
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


@app.post("/users/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(**user_in.dict())
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


@app.post("/news/", response_model=NewsOut, status_code=status.HTTP_201_CREATED)
def create_news(author_id: int, news_in: NewsCreate, db: Session = Depends(get_db)):
    author = db.get(User, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    if not author.is_verified_author:
        raise HTTPException(status_code=403, detail="User is not verified to publish news")
    news = News(author_id=author_id, **news_in.dict())
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
def update_news(news_id: int, news_in: NewsUpdate, db: Session = Depends(get_db)):
    n = db.get(News, news_id)
    if not n:
        raise HTTPException(status_code=404, detail="News not found")
    data = news_in.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(n, k, v)
    db.commit()
    db.refresh(n)
    return n

@app.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(news_id: int, db: Session = Depends(get_db)):
    n = db.get(News, news_id)
    if not n:
        raise HTTPException(status_code=404, detail="News not found")

    db.delete(n)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/comments/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(author_id: int, news_id: int, comment_in: CommentCreate, db: Session = Depends(get_db)):
    author = db.get(User, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    news = db.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    comment = Comment(author_id=author_id, news_id=news_id, **comment_in.dict())
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
def update_comment(comment_id: int, comment_in: CommentUpdate, db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    data = comment_in.dict(exclude_unset=True)
    if "text" in data:
        c.text = data["text"]
    db.commit()
    db.refresh(c)
    return c

@app.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    db.delete(c)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
