import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")
#

lower_url = DATABASE_URL.lower()
if lower_url.startswith("postgres://"):
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL.split("://", 1)[1]
elif lower_url.startswith("postgresql://") and "+" not in lower_url:
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL.split("://", 1)[1]
elif "+psycopg2" in lower_url:
    DATABASE_URL = DATABASE_URL.replace("+psycopg2", "+asyncpg")

engine = create_async_engine(DATABASE_URL, future=True, echo=False)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False, class_=AsyncSession)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
