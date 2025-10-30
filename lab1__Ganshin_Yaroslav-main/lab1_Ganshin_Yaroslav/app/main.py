from fastapi import FastAPI
from .routers import auth, users, news, comments
from .routers import oauth_github

app = FastAPI(title="News API (async, modular)")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(news.router)
app.include_router(comments.router)
app.include_router(oauth_github.router)
