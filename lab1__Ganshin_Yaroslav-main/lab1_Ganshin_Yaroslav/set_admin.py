import os
import sys
import asyncio
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.db import AsyncSessionLocal
from app.models import User
from app.security import hash_password
from sqlalchemy import select


async def set_admin(email: str, new_password: str) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"Пользователь с email={email} не найден.")
            return 1
        user.password_hash = hash_password(new_password)
        user.role = "admin"
        user.is_verified_author = True
        await db.commit()
        await db.refresh(user)
        print("Обновлено:", {"id": user.id, "email": user.email, "role": user.role, "is_verified_author": user.is_verified_author})
        return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python set_admin.py <email> <new_password>")
        sys.exit(1)
    email = sys.argv[1]
    pwd = sys.argv[2]
    code = asyncio.run(set_admin(email, pwd))
    sys.exit(code)
