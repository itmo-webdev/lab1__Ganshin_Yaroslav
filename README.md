
# Лабораторная 1. News API (FastAPI, SQLAlchemy, Alembic)

CRUD-сервис новостей с тремя сущностями:  User ,  News,  Comment .  
Реализованы: создание, просмотр, редактирование, удаление для всех сущностей, правило — публиковать новости могут только верифицированные пользователи; удаление новости удаляет все её комментарии.


Сущности: User, News, Comment (CRUD для всех).

Поля:

User: name, email (unique), registered_at, is_verified_author, avatar.

News: title, content (JSON), published_at, author, cover.

Comment: text, news_id, author_id, published_at.

Правила: только is_verified_author==true может создавать новости.

Удаление новости — каскадно удаляет её комментарии (ORM cascade).

Миграции: настроен Alembic (папка alembic/), есть ревизия seed (файл в alembic/versions).



НОООО
проекте .env содержит строку:

DATABASE_URL=postgresql+psycopg2://labuser:labpass@localhost:5434/labdb

Т.е.  у меня локальный Postgres на localhost:5434 с пользователем labuser/labpass, база labdb.


Т.е. если будете проверять, то:
Отредактировать .env, postgres скачать и поставить ваш DATABASE_URL, ( например ):

DATABASE_URL=postgresql+psycopg2://postgres:pass@127.0.0.1:5432/newsdb





Содержание:
1.  Что в репо  
2.  Минимальные зависимости 
3.  Быстрый запуск    
4.  Миграции (Alembic)  
5. API — ручки и примеры использования  
6. Архитектура и дизайн моделей  
7. Коммиты 


---

## Что в репо
- main.py — основной код: модели SQLAlchemy, Pydantic-схемы, CRUD-эндпоинты, startup и seed.  
-  alembic  — конфигурация миграций.  
-  requirements.txt  — зависимости проекта.   
-  .env  — файл с DATABASE_URL.

---


requirements.txt:

```text
fastapi==0.118.0
uvicorn==0.18.3
SQLAlchemy==2.0.43
psycopg2-binary==2.9.10
pydantic==2.11.9
python-dotenv==1.1.1
alembic>=1.10
```





