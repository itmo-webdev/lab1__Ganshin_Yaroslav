# Модуль: Настройка авторизации через GitHub

Что нужно было исправить?

<img width="1262" height="232" alt="image" src="https://github.com/user-attachments/assets/b1bbb69f-0c69-44f9-bba9-d7ede860ca31" />





## 🔧 Исправление комментариев преподавателя

### 1. **Асинхронность при обращении к БД**
**ИСПРАВЛЕНО:** Все обращения к БД переведены на асинхронный режим:
- Используется `AsyncSession` из SQLAlchemy
- Все функции в роутерах используют `async/await`
- Конкретно (в качестве примера, я все прописывать не буду, чтобы не засорять описание ):
  ```python
  # Было бы синхронно (неправильно):
  # user = db.query(User).filter(User.id == user_id).first()
  
  # Стало асинхронно (правильно):
  result = await db.execute(select(User).where(User.id == user_id))
  user = result.scalar_one_or_none()
  ```

**Исключение:** Celery воркер (`email.py`) использует синхронный доступ, так как Celery не поддерживает async/await в задачах.

### 2. **401 и 403 ошибки только в зависимостях**
**ИСПРАВЛЕНО:** Все ошибки авторизации и доступа вынесены в зависимости:
- **В `dependencies.py`** созданы:
  - `UnauthorizedException` (401 ошибки)
  - `ForbiddenException` (403 ошибки)
- **Убраны из контроллеров** прямые вызовы `HTTPException(401/403)`
- **В роутерах** используются зависимости для проверки прав:
  ```python
  # Пример из news.py - правильный подход
  @router.post("/", response_model=NewsOut)
  async def create_news(
      news_in: NewsCreate,
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(require_verified_author)  # ← зависимость проверяет права
  ):
      # Без проверок прав в теле функции
  ```

### 3. **Реструктуризация проекта**
**ИСПРАВЛЕНО:** Логика вынесена из main.py:
- **Модели**: `models.py` - SQLAlchemy модели
- **Схемы**: `schemas.py` - Pydantic схемы для валидации
- **Роуты по сущностям**:
  - `auth.py` - аутентификация
  - `users.py` - управление пользователями
  - `news.py` - новости
  - `comments.py` - комментарии
  - `oauth_github.py` - OAuth авторизация
- **Бизнес-логика** в соответствующих роутерах
- **Зависимости**: `dependencies.py` - система проверки прав
- **Конфигурация**: `config.py`, `celery_app.py`, `cache.py`

### 4. **Дополнительные исправления**
- **`.env` в `.gitignore`**: Добавлено исключение конфиденциальных файлов
- **Удалены ненужные архивы**: Репозиторий очищен от временных файлов
- **Middleware** для глобальной проверки аутентификации в `main.py`

## 🏗️ Структура проекта после рефакторинга

```
app/

├── main.py              # Точка входа, middleware, конфигурация приложения

├── models.py           # SQLAlchemy модели (User, News, Comment)

├── schemas.py          # Pydantic схемы для валидации

├── dependencies.py     # Зависимости для проверки прав (401/403 ошибки)

├── security.py         # JWT, хэширование паролей

├── cache.py           # Redis кеширование

├── db.py              # Настройка асинхронной БД

├── config.py          # Конфигурация приложения

├── celery_app.py      # Конфигурация Celery

├── metrics.py         # Prometheus метрики

├── logging_config.py  # Настройка структурированного логгирования

├── hawk_config.py     # Интеграция с мониторингом Hawk

├── routers/           # Роуты по сущностям

│   ├── auth.py

│   ├── users.py

│   ├── news.py

│   ├── comments.py

│   └── oauth_github.py

└── tasks/             # Celery задачи

    └── email.py
```



## 📋 Выполнение технического задания

### ✅ Все функциональные требования реализованы:

#### 1. **Авторизация через GitHub OAuth**
- Реализована в модуле `oauth_github.py`
- Используется библиотека `fastapi_sso`
- Роуты: `/api/auth/github` и `/api/auth/github/callback`
- При успешной авторизации генерируются JWT и refresh токены
- Пользователи без аккаунта автоматически регистрируются

#### 2. **Ролевая модель с проверкой прав**
- Модели ролей в `models.py`: `ADMIN`, `MODERATOR`, `AUTHOR`, `USER`
- Зависимости для проверки ролей в `dependencies.py`:
  - `require_role()` - универсальная проверка
  - `require_admin`, `require_moderator`, `require_author`, `require_user` - конкретные роли
  - `require_verified_author` - проверка флага верификации автора

#### 3. **Резолверы для проверки прав на объекты**
- `resolve_news_and_check_editable()` - проверяет права на редактирование новости
- `resolve_comment_and_check_owner()` - проверяет права на редактирование комментария
- Логика проверки вынесена из контроллеров в зависимости

#### 4. **JWT и refresh токены с user agent**
- `security.py`: Генерация и валидация JWT токенов
- `auth.py`: Система refresh сессий с хранением в Redis
- User agent сохраняется в каждой сессии
- Ручка `GET /api/auth/sessions` для просмотра активных сессий

#### 5. **Все необходимые операции с токенами**
- `POST /api/auth/refresh` - обновление токенов
- `POST /api/auth/logout` - выход из системы
- `POST /api/auth/login` - вход по логину/паролю
- `POST /api/auth/register` - регистрация

#### 6. **Хэширование паролей**
- Используется `argon2` для безопасного хэширования
- Функции `hash_password()` и `verify_password()` в `security.py`

### ✅ Нефункциональные требования выполнены:

- **Python 3.10+**: Код совместим с указанной версией
- **Библиотеки**: Используются FastAPI, SQLAlchemy, fastapi_sso, argon2
- **PostgreSQL**: Асинхронный драйвер `asyncpg`
- **Корректный запуск**: Приложение стартует без ошибок
- **.env конфигурация**: Пример файла `.env.example` с настройками GitHub OAuth


### Особенности:
- **Флаг `is_verified_author`**: Даже при роли AUTHOR без этого флага нельзя создавать новости
- **Проверка владения**: Пользователь может редактировать только свои объекты (кроме админов и модераторов)
- **Публичный доступ**: GET-запросы к новостям и комментариям доступны без авторизации

1. **Кеширование**:
   - Кеширование пользователей в Redis (TTL 10 мин)
   - Кеширование новостей (TTL 5 мин)
   - Инвалидация кеша при изменениях

2. **Мониторинг**:
   - Prometheus метрики (`/metrics`)
   - Структурированное логгирование через structlog
   - Интеграция с Hawk для мониторинга ошибок

3. **Отказоустойчивость**:
   - Повторные попытки в Celery задачах
   - Health check эндпоинт (`/health`)
   - Graceful shutdown






# Новостной API (FastAPI)

## О проекте
Современный асинхронный API для управления новостями с системой аутентификации и авторизации. Проект использует FastAPI, SQLAlchemy, Celery и Redis.

## Основные технологии

### Асинхронность
- Все эндпоинты объявлены с `async def` для поддержки асинхронной обработки
- Используется `AsyncSession` из SQLAlchemy для работы с базой данных
- **FastAPI** для асинхронной обработки запросов
- **SQLAlchemy 2.0** с асинхронной поддержкой для работы с базой данных
- **Alembic** для миграций базы данных

### Воркер для отправки email
- **Celery** в качестве асинхронного обработчика задач
- Отдельная очередь `email` для обработки почтовых уведомлений
- Настройки воркера включают:
  - Позднее подтверждение задач (`task_acks_late=True`)
  - Автоматическая отмена зависших задач
  - Поддержка таймзоны (настраивается через переменную окружения `TZ`)

### Кеширование
- **Redis** в качестве кеш-хранилища
- Асинхронный клиент Redis для работы с кешем
- Поддержка различных типов данных:
  - Простые ключ-значение
  - JSON-сериализация для сложных объектов
  - Работа с множествами (sets)
- Удаление по префиксу для инвалидации групп ключей

### Аутентификация и авторизация
- JWT (JSON Web Tokens) для аутентификации
- Два типа токенов:
  - Access токен (короткоживущий, 15 минут по умолчанию)
  - Refresh токен (долгоживущий, 24 часа по умолчанию)
- Хеширование паролей с использованием Argon2
- Интеграция с GitHub OAuth
- Middleware для проверки аутентификации

## Запуск проекта

### Требования
- Python 3.9+
- Redis
- PostgreSQL
- Установленные зависимости из `requirements.txt`

### Настройка окружения
1. Создайть файл `.env` в корне проекта на основе `.env.example` ( мой я сюда не загружал, чтобы не подвергать риску чувствительную информацию )
2. Заполните необходимые переменные окружения:
   - `DATABASE_URL` - URL для подключения к PostgreSQL
   - `JWT_SECRET` - секретный ключ для подписи JWT
   - `REDIS_URL` - URL для подключения к Redis
   - `CELERY_BROKER_URL` - URL для брокера сообщений Celery (по умолчанию используется Redis)
   - Настройки SMTP для отправки email
  
 
  Запуск через uvicorn app.main:app --reload 
  
  Можно использовать файл Докера... ( docker-compose.yml конкретно тут не используем, т.к. он для бек + фронт, тут нету папки с frontend, соотв., учитываем )



### Установка зависимостей
bash
pip install -r requirements.txt




Теперь быстро протестирую функционал:


Необходимо закрыть все ручки
<img width="897" height="430" alt="image" src="https://github.com/user-attachments/assets/b9f8a5e5-b924-48b0-b135-54a4df0510f7" />

<img width="1224" height="345" alt="image" src="https://github.com/user-attachments/assets/4d19fe7e-c7ba-49d0-b412-967fedb4049a" />


 
Необходимо поддержать авторизацию через GitHub OAuth
  <img width="218" height="179" alt="image" src="https://github.com/user-attachments/assets/69e4f8e9-b7c4-48e2-b06f-273a9e059f3a" />


Необходимо поддержать флаг "верифицирован ли как автор" при попытке создать новость
<img width="463" height="171" alt="image" src="https://github.com/user-attachments/assets/6c6032af-0bdb-4e91-9bf2-c84ef1bff723" />

Обновить флаг для админов, которые могу выполнять все операции.Роль тут будет либо юзер либо админ.

<img width="697" height="304" alt="image" src="https://github.com/user-attachments/assets/b72fcf62-74dd-4c97-90ad-84cb838a9caa" />

Сценарий использования
Запустить локально сервис
Можно авторизоваться через GitHub, так же можно авторизовать через логин и пароль, нужны для этого дополнительные ручки
Если пользователь не верифицирован как автор, то создать новость он не может
Пользователь может редактировать свою же новость, помимо этого и удалять
Комментарии могут оставлять любые пользователи, авторы комментариев могут их редактировать и удалять
Пользователь с ролью админ может делать все вышеперечисленное\

Если пользователь не верифицирован как автор, то создать новость он не может

<img width="1244" height="574" alt="image" src="https://github.com/user-attachments/assets/043ba16e-ffd2-4ac0-b56f-b0b695e739c8" />



Создание API для новостей

1)
Нужно написать CRUD API, используя FastAPI, который содержит следующие сущности:
Новость
Пользователь
Комментарий

<img width="1067" height="584" alt="image" src="https://github.com/user-attachments/assets/46f14268-9b11-407b-91c1-1ebb8815cf95" />

<img width="1059" height="548" alt="image" src="https://github.com/user-attachments/assets/905bd3b8-ea5d-4a90-82bc-698fb5665d03" />

<img width="1060" height="629" alt="image" src="https://github.com/user-attachments/assets/fb7bfba4-44f7-4e1d-81c7-bb44d53bc43b" />

Сценарий использования
Запустить локально сервис
Создать пользователей
Создать новость, которая прикреплена к пользователю (автор)
Создать комментарий к новости от другого пользователя
Изменить новость
Изменить комментарий
Удалить новость вместе со всеми комментариями
<img width="1176" height="126" alt="image" src="https://github.com/user-attachments/assets/c8ac4fd1-6b52-444d-8e81-69028a12dcba" />

<img width="1221" height="613" alt="image" src="https://github.com/user-attachments/assets/ed4a7bfc-c4cf-4949-8965-2d39b128da6e" />

Создам пользователя:

<img width="987" height="587" alt="image" src="https://github.com/user-attachments/assets/f32564b1-dfdd-4dca-84d1-2d1121041ebd" />

<img width="957" height="620" alt="image" src="https://github.com/user-attachments/assets/311b516b-79e3-4abb-978b-6d36b13801b6" />

Чтобы запостить новость, мне нужно авторизироваться и зайти как автор:
<img width="893" height="317" alt="image" src="https://github.com/user-attachments/assets/b2f3a22e-9198-422a-a94a-959d5ec66136" />

Для этого сделаю пользователя автором:
(залогинюсь как админ для начала )
<img width="722" height="597" alt="image" src="https://github.com/user-attachments/assets/a0fd9ee0-8fd1-41c4-9105-eb1a68c1f027" />

<img width="952" height="473" alt="image" src="https://github.com/user-attachments/assets/2c01384e-1c76-4dc5-ac31-68921d6271aa" />

Сделаю моего пользователя автором

<img width="978" height="567" alt="image" src="https://github.com/user-attachments/assets/af4bb24a-7c0a-476f-af0f-a582dca23a32" />

<img width="1019" height="643" alt="image" src="https://github.com/user-attachments/assets/33571aa8-2842-417e-a772-38e773252b22" />

<img width="1076" height="516" alt="image" src="https://github.com/user-attachments/assets/f5b086b5-8bc9-4ece-8038-0ab1c94eaac4" />

<img width="1044" height="557" alt="image" src="https://github.com/user-attachments/assets/e63234f6-df6b-4008-9a3d-a3c05060da40" />
<img width="1028" height="585" alt="image" src="https://github.com/user-attachments/assets/5094d9b0-d516-4bba-99f9-9f0599521f33" />
<img width="851" height="635" alt="image" src="https://github.com/user-attachments/assets/5bb47c58-0e7b-41b7-a0d1-4d6dbbb38f0d" />
<img width="989" height="564" alt="image" src="https://github.com/user-attachments/assets/fba9e9f5-2e75-4148-bb7b-af36819ad099" />
<img width="1098" height="624" alt="image" src="https://github.com/user-attachments/assets/37a2adee-4426-4848-9116-02c39b5ef9c3" />
<img width="512" height="201" alt="image" src="https://github.com/user-attachments/assets/69181c0d-bf7b-4036-9e43-5fc52939cb34" />

















