import os
from dotenv import load_dotenv

load_dotenv() 


FRONTEND_URL = os.getenv("FRONTEND_URL")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REDIS_URL = os.getenv("REDIS_URL")
