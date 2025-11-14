from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import News, User
from ..schemas import NewsCreate, NewsUpdate, NewsOut
from ..dependencies import get_current_user, require_verified_author, resolve_news_and_check_editable
from ..cache import get_json, set_json, delete as cache_delete, delete_by_prefix
from ..celery_app import app as celery_app

router = APIRouter(prefix="/news", tags=["news"])
_NEWS_TTL = 300

@router.post("/", response_model=NewsOut, status_code=status.HTTP_201_CREATED)
async def create_news(news_in: NewsCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_verified_author)):
    news = News(author_id=current_user.id, **news_in.dict())
    db.add(news)
    await db.commit()
    await db.refresh(news)

    await cache_delete(f"news:{news.id}")
    await delete_by_prefix("news:list:")
    celery_app.send_task(
        "lab1_Ganshin_Yaroslav.app.tasks.email.notify_new_news",
        args=[news.id],
        queue="email",
    )
    return news

@router.get("/{news_id}", response_model=NewsOut)
async def read_news(news_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    cached = await get_json(f"news:{news_id}")
    if cached:
        return cached
    result = await db.execute(
        select(News).options(selectinload(News.author)).where(News.id == news_id)
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="News not found")
    item = NewsOut.model_validate(n).model_dump()
    await set_json(f"news:{news_id}", item, ttl_seconds=_NEWS_TTL)
    return item

@router.get("/", response_model=List[NewsOut])
async def list_news(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    key = f"news:list:{skip}:{limit}"
    cached = await get_json(key)
    if cached:
        return cached
    result = await db.execute(
        select(News).options(selectinload(News.author)).offset(skip).limit(limit)
    )
    items = [NewsOut.model_validate(n).model_dump() for n in result.scalars().all()]
    await set_json(key, items, ttl_seconds=_NEWS_TTL)
    return items

@router.put("/{news_id}", response_model=NewsOut)
async def update_news(news_id: int, news_in: NewsUpdate, news: News = Depends(resolve_news_and_check_editable), db: AsyncSession = Depends(get_db)):
    data = news_in.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(news, k, v)
    await db.commit()
    await db.refresh(news)

    await cache_delete(f"news:{news.id}")
    await delete_by_prefix("news:list:")
    return news

@router.delete("/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(news_id: int, news: News = Depends(resolve_news_and_check_editable), db: AsyncSession = Depends(get_db)):
    await db.delete(news)
    await db.commit()

    await cache_delete(f"news:{news_id}")
    await delete_by_prefix("news:list:")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
