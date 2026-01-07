# 📰 News API with Email Worker

## Описание
**Полностью работоспособный новостной API с фоновой обработкой email-уведомлений**, реализующий все требования задания по добавлению Celery воркера. Система обеспечивает мгновенные уведомления о новых новостях и еженедельные дайджесты с гарантированной доставкой и защитой от дублирования.

## 📋 Выполненные требования ТЗ

### ✅ Все функциональные требования реализованы:

| Требование | Статус | Где реализовано |
|------------|--------|-----------------|
| Celery + Redis как брокер | ✅ | `celery_app.py`, `docker-compose.yml` |
| Ретраи с exponential backoff | ✅ | Декораторы `@shared_task` в `email.py` |
| Graceful shutdown | ✅ | Настройки в `celery_app.py` |
| Идемпотентность отправки | ✅ | Redis sets + TTL ключи в `email.py` |
| Моковые уведомления (логирование) | ✅ | Логирование в `logs/email_worker.log` |
| Две задачи: мгновенная + еженедельная | ✅ | `notify_new_news()` + `weekly_digest()` |
| Логирование выполняемых задач | ✅ | RotatingFileHandler в `email.py` |

## 🏗️ Архитектура

```
docker-compose.yml          # Все сервисы в одном месте
├── redis:6379             # Брокер сообщений для Celery
├── web:8000               # FastAPI приложение
├── worker                 # Celery worker (обработка email)
├── beat                   # Celery beat (расписание)
└── frontend:5173          # Vue.js фронтенд (опционально)
```

## Быстрый старт

### Вариант: Локальный запуск
```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите Redis
docker run -d -p 6379:6379 redis:7

# Настройте .env файл (скопируйте из .env.example)
cp .env.example .env

# Запустите компоненты в разных терминалах:
# 1. FastAPI сервер
uvicorn app.main:app --reload

# 2. Celery worker
celery -A app.celery_app worker --loglevel=info -Q email,default

# 3. Celery beat
celery -A app.celery_app beat --loglevel=info
```

## 📨 Email Worker

### 🔔 Мгновенные уведомления
При создании новости автоматически отправляется задача:
```python
# news.py
celery_app.send_task("app.tasks.email.notify_new_news", args=[news.id], queue="email")
```

**Что происходит:**
1. Задача попадает в Redis очередь `email`
2. Worker обрабатывает её асинхронно
3. Для каждого пользователя проверяется, не отправлялось ли уже уведомление (идемпотентность через Redis Set)
4. Логируется "отправка" в файл `logs/email_worker.log`

### 📅 Еженедельный дайджест
Каждое воскресенье в 09:00 система автоматически:
1. Собирает все новости за последние 7 дней
2. Формирует дайджест для каждого пользователя
3. Проверяет, не отправлялся ли уже дайджест этой недели (TTL ключи на 14 дней)
4. Логирует результат

## 📊 Логирование и мониторинг

### Пример реальных логов из тестирования:
```
2025-11-14 02:43:32 INFO send_mock {"type": "weekly_digest", "to_user_id": 1, "to_email": "user1@example.com", ...}
2025-11-14 02:43:32 INFO send_mock {"type": "weekly_digest", "to_user_id": 2, "to_email": "user2@example.com", ...}
```

**Файлы логов:**
- `logs/email_worker.log` - логи email задач (ротация: 2MB × 3 файла)
- Автоматическое создание директории при старте

### Health Check эндпоинт:
```bash
GET /health
```
**Проверяет:** PostgreSQL, Redis, Celery
**Ответ:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-14T02:43:32.123456",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "celery": "healthy"
  }
}
```

## Технические особенности

### Идемпотентность (защита от дублирования)
```python
# Для мгновенных уведомлений - Redis Set
key = f"email:sent:news:{news.id}"
added = r.sadd(key, str(user_id))  # 0 = уже отправлялось

# Для дайджестов - TTL ключи (14 дней)
key = f"email:sent:digest:{week}:{user_id}"
if r.get(key):  # Ключ существует = уже отправляли
    continue
```

### Надёжность (Graceful Shutdown)
```python
# celery_app.py
task_reject_on_worker_lost=True,      # Отклоняем задачи при потере воркера
worker_cancel_long_running_tasks_on_connection_loss=True,  # Отменяем зависшие
task_acks_late=True,                  # Подтверждение после выполнения
```

### Ретраи с Exponential Backoff
```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),        # Ретраи при любых исключениях
    retry_backoff=5,                   # Начальная задержка 5 сек
    retry_backoff_max=300,             # Максимальная задержка 300 сек
    retry_jitter=True,                 + Случайный разброс
    max_retries=5                      # Максимум 5 попыток
)
```

## Результаты тестирования

**Полностью работоспособно:**
- [x] Создание новости → мгновенные уведомления всем пользователям
- [x] Еженедельный дайджест по расписанию (воскресенье 09:00)
- [x] Идемпотентность (нет дублирующих уведомлений)
- [x] Ретраи при ошибках (exponential backoff)
- [x] Graceful shutdown воркера
- [x] Логирование в файл с ротацией
- [x] Health check всех компонентов

> Система полностью соответствует ТЗ задания "Добавить email воркер".  
> Все функциональные и нефункциональные требования реализованы.  
> Логи работы доступны в `logs/email_worker.log`, демонстрируя корректную работу еженедельного дайджеста и мгновенных уведомлений.

<img width="1741" height="281" alt="image" src="https://github.com/user-attachments/assets/b33581d8-9cc0-4024-b2e8-32dad6062bf3" />


<img width="1668" height="462" alt="image" src="https://github.com/user-attachments/assets/18f5a183-ba28-4069-9922-6d5ec548e921" />

