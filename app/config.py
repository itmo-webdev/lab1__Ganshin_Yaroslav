import os
from dotenv import load_dotenv
<<<<<<< HEAD
=======

load_dotenv() 
>>>>>>> 035c268e2597b4667746047a83ef0fab8e2c2591

load_dotenv() 

FRONTEND_URL = os.getenv("FRONTEND_URL")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REDIS_URL = os.getenv("REDIS_URL")
