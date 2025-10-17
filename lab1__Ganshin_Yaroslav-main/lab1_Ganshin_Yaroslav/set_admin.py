import os
import sys
from dotenv import load_dotenv

# Подключаем проектный main, чтобы использовать те же модели/SessionLocal/функции
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Загружаем .env, если он есть
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

try:
    # импортируем объекты из main.py
    from main import SessionLocal, User, hash_password
except Exception as e:
    print("Ошибка при импорте из main.py:", e)
    raise

def set_admin(email: str, new_password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Пользователь с email={email} не найден.")
            return 1
        # хешируем пароль и ставим роль admin и помечаем is_verified_author True
        user.password_hash = hash_password(new_password)
        user.role = "admin"
        user.is_verified_author = True
        db.add(user)
        db.commit()
        db.refresh(user)
        print("Обновлено:", {"id": user.id, "email": user.email, "role": user.role, "is_verified_author": user.is_verified_author})
        return 0
    except Exception as e:
        print("Ошибка при обновлении:", e)
        db.rollback()
        return 2
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python set_admin.py <email> <new_password>")
        sys.exit(1)
    email = sys.argv[1]
    pwd = sys.argv[2]
    sys.exit(set_admin(email, pwd))
