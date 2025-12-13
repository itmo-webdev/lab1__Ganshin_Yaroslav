import os
from dotenv import load_dotenv

load_dotenv() 

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0") # Добавляем REDIS_URL
