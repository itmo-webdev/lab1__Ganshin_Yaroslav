from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..models import Comment, News, User
from ..schemas import CommentCreate, CommentUpdate, CommentOut
from ..dependencies import get_current_user, resolve_comment_and_check_owner

router = APIRouter(prefix="/comments", tags=["comments"])

@router.post("/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(news_id: int, comment_in: CommentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    news_res = await db.execute(select(News).where(News.id == news_id))
    news = news_res.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    comment = Comment(author_id=current_user.id, news_id=news_id, **comment_in.dict())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    comment.author = current_user
    return comment

@router.get("/{comment_id}", response_model=CommentOut)
async def read_comment(comment_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    c = await db.get(Comment, comment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    return c

@router.put("/{comment_id}", response_model=CommentOut)
async def update_comment(comment_id: int, comment_in: CommentUpdate, db: AsyncSession = Depends(get_db), c: Comment = Depends(resolve_comment_and_check_owner)):
    data = comment_in.dict(exclude_unset=True)
    if "text" in data:
        c.text = data["text"]
    await db.commit()
    await db.refresh(c)
    return c

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, db: AsyncSession = Depends(get_db), c: Comment = Depends(resolve_comment_and_check_owner)):
    await db.delete(c)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from typing import List
from sqlalchemy.orm import selectinload

@router.get("/", response_model=List[CommentOut])
async def list_comments(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .order_by(Comment.published_at)
        .offset(skip)
        .limit(limit)
    )
    comments = result.scalars().all()
    return [CommentOut.model_validate(c).model_dump(mode='json') for c in comments]

from typing import List
from sqlalchemy.orm import selectinload

@router.get("/news/{news_id}", response_model=List[CommentOut])
async def list_comments_for_news(news_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.news_id == news_id)
        .order_by(Comment.published_at)
        .offset(skip)
        .limit(limit)
    )
    comments = result.scalars().all()
    return [CommentOut.model_validate(c).model_dump(mode='json') for c in comments]
