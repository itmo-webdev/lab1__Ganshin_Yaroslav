import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.models import User
from app.security import hash_password


def _make_sync_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    lower = url.lower()
    if "+asyncpg" in lower:
        return url.replace("+asyncpg", "+psycopg2")
    if lower.startswith("postgres://"):
        return "postgresql+psycopg2://" + url.split("://", 1)[1]
    if lower.startswith("postgresql://") and "+" not in lower:
        return "postgresql+psycopg2://" + url.split("://", 1)[1]
    return url


def set_admin(email: str, new_password: str) -> int:
    engine = create_engine(_make_sync_db_url(), poolclass=NullPool, future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        result = db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"Пользователь с email={email} не найден.")
            return 1
        user.password_hash = hash_password(new_password)
        user.role = "admin"
        user.is_verified_author = True
        db.commit()
        db.refresh(user)
        print("Обновлено:", {"id": user.id, "email": user.email, "role": user.role, "is_verified_author": user.is_verified_author})
        return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python set_admin.py <email> <new_password>")
        sys.exit(1)
    email = sys.argv[1]
    pwd = sys.argv[2]
    code = set_admin(email, pwd)
    sys.exit(code)
