from __future__ import with_statement
import os
import sys
from dotenv import load_dotenv
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context


CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


config = context.config
fileConfig(config.config_file_name)


try:
    from app.models import Base  
except Exception as e:
    raise RuntimeError("Не удалось импортировать Base из app.models: " + str(e))

target_metadata = Base.metadata


load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = config.get_main_option("sqlalchemy.url")

# Alembic must use a SYNC driver. Normalize URL accordingly.
lower_url = (DATABASE_URL or "").lower()
if lower_url.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL.split("://", 1)[1]
if "+asyncpg" in lower_url:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "+psycopg2")
elif lower_url.startswith("postgresql://") and "+" not in lower_url:
    # no explicit driver -> psycopg2 by default
    pass

def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=DATABASE_URL,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
