"""seed mock data

Revision ID: 20251028_200000_seed
Revises: 6a66fbe4e264
Create Date: 2025-10-28 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Integer, String, Boolean, DateTime, Text
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '20251028_200000_seed'
down_revision: Union[str, Sequence[str], None] = '6a66fbe4e264'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    users = table(
        'users',
        column('id', Integer),
        column('name', String),
        column('email', String),
        column('registered_at', DateTime),
        column('is_verified_author', Boolean),
        column('avatar', String),
        column('password_hash', String),
        column('role', String),
    )

    op.execute(users.insert().values([
        {
            'id': 1,
            'name': 'Alice Admin',
            'email': 'alice@example.com',
            'registered_at': datetime.utcnow(),
            'is_verified_author': True,
            'avatar': None,
            'password_hash': None,
            'role': 'admin',
        },
        {
            'id': 2,
            'name': 'Bob User',
            'email': 'bob@example.com',
            'registered_at': datetime.utcnow(),
            'is_verified_author': False,
            'avatar': None,
            'password_hash': None,
            'role': 'user',
        },
    ]))

    news = table(
        'news',
        column('id', Integer),
        column('title', String),
        column('content', sa.dialects.postgresql.JSONB),
        column('published_at', DateTime),
        column('cover', String),
        column('author_id', Integer),
    )

    op.execute(news.insert().values({
        'id': 1,
        'title': 'Первая новость',
        'content': {'blocks': [{'type': 'p', 'text': 'Hello world'}]},
        'published_at': datetime.utcnow(),
        'cover': None,
        'author_id': 1,
    }))

    comments = table(
        'comments',
        column('id', Integer),
        column('text', Text),
        column('published_at', DateTime),
        column('news_id', Integer),
        column('author_id', Integer),
    )

    op.execute(comments.insert().values({
        'id': 1,
        'text': 'Крутая новость!'
        , 'published_at': datetime.utcnow(),
        'news_id': 1,
        'author_id': 2,
    }))


def downgrade() -> None:
    op.execute("DELETE FROM comments WHERE id=1")
    op.execute("DELETE FROM news WHERE id=1")
    op.execute("DELETE FROM users WHERE id in (1,2)")
