
Лабораторная 1. News API (FastAPI, SQLAlchemy, Alembic)
Новостной CRUD‑сервис с сущностями: User, News, Comment. Все операции на БД выполнены асинхронно (SQLAlchemy Async + asyncpg). Авторизация через JWT и GitHub OAuth, права и 401/403 применяются только зависимостями.

Возможности
- Полный CRUD для User/News/Comment
- Только verified авторы (или admin) могут создавать новости
- Редактирование/удаление новости/комментария — владелец или admin
- JWT + refresh, хранение user‑agent, список активных сессий
- GitHub OAuth вход

Архитектура
- app/
  - db.py — AsyncEngine/AsyncSession (runtime: asyncpg)
  - models.py — SQLAlchemy модели (User, News, Comment, RefreshSession)
  - schemas.py — Pydantic‑схемы
  - security.py — argon2, JWT (encode/decode)
  - dependencies.py — аутентификация/авторизация (401/403 только здесь), резолверы сущностей
  - routers/ — роутеры: auth, oauth_github, users, news, comments
  - main.py — сборка FastAPI и подключение роутеров
- alembic/
  - env.py — конфигурация Alembic (sync‑драйвер psycopg2 для миграций)
  - versions/ — initial + seed миграции

Требования
- Python 3.10+
- Postgres
- Зависимости: см. `lab1_Ganshin_Yaroslav/requirements.txt`

Настройка окружения
1) Создайте `.env` (не коммитить, файл уже в .gitignore):
```
DATABASE_URL=postgresql://USER:PASS@127.0.0.1:5432/DBNAME
JWT_SECRET=change_me
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_REDIRECT_URI=http://127.0.0.1:8000/auth/github/callback
```
Примечание: runtime автоматически использует async‑драйвер `+asyncpg`, Alembic — sync (psycopg2).

2) Установите зависимости:
```
pip install -r lab1_Ganshin_Yaroslav/requirements.txt
```

3) Примените миграции:
```
alembic upgrade head
```

4) Запустите приложение:
```
uvicorn app.main:app --reload
```

Быстрый старт (через Swagger)
- Откройте http://127.0.0.1:8000/docs
- Зарегистрируйтесь `/auth/register` → залогиньтесь `/auth/login`
- К защищённым ручкам добавляйте заголовок `Authorization: Bearer <access_token>`
- Обновление токена `/auth/refresh`, выход `/auth/logout`, список сессий `/auth/sessions`
- GitHub OAuth: перейдите в браузере по `/auth/github/login`

Примеры (curl)
Регистрация:
```
curl -X POST http://127.0.0.1:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"User A","email":"user@example.com","password":"Passw0rd!"}'
```
Логин:
```
curl -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"Passw0rd!"}'
```
Создание новости (требуется verified автор или admin):
```
curl -X POST http://127.0.0.1:8000/news \
  -H "Authorization: Bearer <ACCESS>" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Первая новость","content":{"blocks":[{"type":"p","text":"Hello"}]},"cover":null}'
```

Роли и доступ
- Роли: `user`, `admin`
- 401/403 генерируются только зависимостями в `app/dependencies.py`
- Подробнее: см. `docs/auth.md`

Безопасность секретов
- Все секреты в `.env` (не коммитятся). Проверьте `git status`: `.env` должен быть untracked
- Если `.env` когда‑либо попадал в историю git — поменяйте секреты (JWT, OAuth) и, по необходимости, очистите историю

Примечания
- Все обращения к БД — асинхронные (AsyncSession + await)
- Alembic миграции запускаются отдельно от приложения
- Удаление новости каскадом удаляет комментарии (FK on delete + ORM cascade)

 Кэширование и Redis (кратко)
- Redis URL: `REDIS_URL` (пример: `redis://localhost:6379/0`)
- Ключи:
  - `news:{id}` — деталь новости (TTL 300 сек)
  - `news:list:{skip}:{limit}` — список новостей (TTL 300 сек)
  - `rs:{token}` — refresh‑сессия (TTL = `REFRESH_TOKEN_EXPIRE_MINUTES * 60`)
  - `rs_user:{user_id}` — множество refresh‑токенов пользователя
  - `user:{id}` — кэш пользователя без чувствительных данных (TTL ~600 сек)
- Инвалидация:
  - На `POST/PUT/DELETE /news` удаляются `news:{id}` и все `news:list:*`
- Логи hit/miss:
  - Включены в `app/cache.py` (logger `cache`): `cache.hit`, `cache.miss`, `cache.set`, `cache.del*`
  - Запускайте uvicorn и смотрите вывод, чтобы видеть из кэша ли ответ
