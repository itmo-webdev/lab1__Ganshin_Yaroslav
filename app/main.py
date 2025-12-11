from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from .security import decode_access_token
from .routers import auth, users, news, comments
from .routers import oauth_github

app = FastAPI(title="News API (async, modular)")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(news.router)
app.include_router(comments.router)
app.include_router(oauth_github.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

class RoleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith('/admin'):
            auth = request.headers.get('authorization', '')
            if not auth.lower().startswith('bearer '):
                return Response(status_code=401, content='Unauthorized')
            token = auth.split(' ', 1)[1]
            try:
                payload = decode_access_token(token)
            except Exception:
                return Response(status_code=401, content='Unauthorized')
            role = payload.get('role')
            if role != 'admin':
                return Response(status_code=403, content='Forbidden')
        response = await call_next(request)
        return response

@app.get('/admin/ping')
async def admin_ping():
    return {'status': 'ok'}

app.add_middleware(RoleMiddleware)
