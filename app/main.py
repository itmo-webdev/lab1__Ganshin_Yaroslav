
import os
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from datetime import datetime
# Метрики
from prometheus_fastapi_instrumentator import Instrumentator

from app.hawk_config import hawk_client

# новое логгирование
from app.logging_config import setup_hybrid_logging
import structlog




logger = setup_hybrid_logging()
#старый логер, пока не удаляю, чтобы не ломать старый код
legacy_logger = logging.getLogger(__name__)
# Импорт модулей
try:
    from .security import decode_access_token
    from .routers import auth, users, news, comments, oauth_github
    from .db import engine
    from .models import Base
    from .config import FRONTEND_URL  
    

    from .dependencies import get_current_user
    
    # Импортируем Celery для health чека
    from .celery_app import app as celery_app
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    raise

def create_app() -> FastAPI:
    app = FastAPI(
        title="News API",
        description="A modern async news API with authentication and authorization",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Включаем роутеры
    try:
        app.include_router(auth.router, prefix="/api", tags=["auth"])
        app.include_router(users.router, prefix="/api/users", tags=["users"])
        app.include_router(news.router, prefix="/api", tags=["news"])
        app.include_router(comments.router, prefix="/api", tags=["comments"])
        app.include_router(oauth_github.router, prefix="/api", tags=["oauth"])
    except Exception as e:
        logger.error(f"Failed to include routers: {e}")
        raise
        
    return app

app = create_app()
#метрики
instrumentator = Instrumentator().instrument(app)
def setup_middleware(app: FastAPI) -> None:
    # Миддлвеар
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        FRONTEND_URL,
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

# Настраиваем миддлвеар
setup_middleware(app)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        import time
        start_time = time.time()
        
        #  structlog для новых JSON логов ( еще раз - у меня осталось старое логирование, к нему я добавил новое)
        logger.info(
            "incoming_request",
            method=request.method,
            path=request.url.path,
            ip=request.client.host if request.client else None
        )
        
        # старый лог для совместимости
        legacy_logger.info(f"Incoming request: {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # JSON логи
            logger.info(
                "response",
                status_code=response.status_code,
                process_time=process_time,
                method=request.method,
                path=request.url.path
            )
            
            # Старые логи
            legacy_logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
            
            return response
            
        except Exception as e:
            # Оба типа логов
            logger.error("unhandled_exception", exception=str(e), exc_info=True)
            legacy_logger.error(f"Unhandled exception: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        # Пропускаем публичные маршруты
        public_paths = [
            "/", "/health", "/api/docs", "/api/openapi.json", "/api/redoc",
            "/api/auth/login", "/api/auth/register", "/api/auth/refresh",
            "/api/auth/github", "/api/auth/github/", "/api/auth/github/callback",
            "/api/news", "/api/news/", "/api/news/{news_id}",
            "/api/comments", "/api/comments/news/{news_id}",
            "/api/users", "/metrics",
            "/test-hawk-error",
            "/test-hawk-error",
            "/favicon.ico",
            "/.well-known"
        ]
        
        if any(request.url.path.startswith(path.replace("{news_id}", "").rstrip("/")) 
               for path in public_paths if "{news_id}" in path) or \
           request.url.path in public_paths:
            return await call_next(request)
        
        # Проверяем токен для защ. маршрутов
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = auth_header.split(" ")[1]
        try:
            payload = decode_access_token(token)
            # Добавляем информацию о пользователе в request.state
            request.state.user_id = payload.get("sub")
            request.state.user_role = payload.get("role")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return await call_next(request)

# Добавляем middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthenticationMiddleware)

# События жизненного цикла
@app.on_event("startup")
async def startup_event():
    """Создание таблиц при запуске"""
    logger.info("Starting up...")
    
    # Создаем директорию для логов, соотв., понятно, если ее нету
    logs_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        logger.info(f"Created logs directory: {logs_dir}")
    #метрики
    instrumentator.expose(app)
    # Создаем таблицы в базе данных
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении"""
    logger.info("Shutting down...")
    await engine.dispose()

# Основные маршруты
@app.get("/")
async def root():
    """Корневой маршрут"""
    return {
        "message": "News API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья системы"""
    import asyncio
    from redis.asyncio import Redis
    from sqlalchemy import text
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Проверка базы данных
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            health_status["components"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["components"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Проверка редиса
    try:
        from .config import REDIS_URL
        redis_client = Redis.from_url(REDIS_URL)
        await redis_client.ping()
        health_status["components"]["redis"] = "healthy"
        await redis_client.close()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["components"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Проверка Celery
    try:
        # Простая проверка, что Celery приложение загружено
        if celery_app:
            health_status["components"]["celery"] = "healthy"
        else:
            health_status["components"]["celery"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        health_status["components"]["celery"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status

# Admin маршруты
@app.get("/api/admin/ping")
async def admin_ping(current_user = Depends(get_current_user)):
    """Проверка доступа админа"""
    from app.models import UserRole
    from app.dependencies import require_role
    
    # Проверяем роль через dependency
    admin_check = require_role(UserRole.ADMIN)
    await admin_check(current_user)
    
    return {
        "status": "pong", 
        "message": "Admin access granted",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role
        }
    }

# GitHub OAuth redirect helper
@app.get("/login/github")
async def github_login_redirect():
    """Перенаправление на GitHub OAuth"""
    return RedirectResponse(url="/api/auth/github")

# Обработчик ошибок

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений В JSON + Hawk"""
    
    # Логируем
    logger.warning(
        "http_error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    legacy_logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
    
    # Отправляем в Hawk только серверные ошибки (5xx и т.п.)
    if exc.status_code >= 500:
        try:
            hawk_client.send(
                exc,
                extra={
                    "status_code": exc.status_code,
                    "path": request.url.path,
                    "method": request.method,
                    "detail": exc.detail
                }
            )
        except Exception as hawk_error:
            logger.error("hawk_error", error=str(hawk_error))
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers if hasattr(exc, 'headers') else {}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик общих исключений В JSON + Hawk"""
    
    # Логируем
    logger.error(
        "unhandled_exception",
        exception=str(exc),
        exc_info=True,
        path=request.url.path,
        method=request.method
    )
    legacy_logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Отправляем в Hawk
    try:
        hawk_client.send(
            exc,
            extra={
                "path": request.url.path,
                "method": request.method,
                "request_url": str(request.url)
            }
        )
    except Exception as hawk_error:
        logger.error("hawk_error", error=str(hawk_error))
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/test-hawk-error")
async def test_hawk_error():
    """Тестовый эндпоинт для проверки Hawk (удалить после теста)"""
    try:
        # Генерируем ошибку
        raise ValueError("Тестовая ошибка для Hawk мониторинга")
    except Exception as e:
        # Логируем и отправляем в Hawk
        logger.error("test_hawk_error", error=str(e))
        hawk_client.send(e, extra={"test": True})
        # Возвращаем JSON-ответ вместо повторного вызова raise
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Тестовая ошибка отправлена в Hawk",
                "error": str(e)
            }
        )
# Опционально: добавим эндпоинт для получения конфигурации
@app.get("/api/config")
async def get_config():
    """Получение публичной конфигурации"""
    from app.config import (
        GITHUB_CLIENT_ID,
        FRONTEND_URL,
        ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return {
        "github_oauth_available": bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_ID != "your_github_client_id"),
        "frontend_url": FRONTEND_URL,
        "access_token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES
    }