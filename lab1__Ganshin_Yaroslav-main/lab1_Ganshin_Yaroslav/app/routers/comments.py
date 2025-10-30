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
