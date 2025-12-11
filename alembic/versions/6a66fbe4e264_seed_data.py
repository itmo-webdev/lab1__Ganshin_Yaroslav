"""initial schema

Revision ID: 6a66fbe4e264
Revises: 
Create Date: 2025-10-03 01:25:12.810597

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6a66fbe4e264'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('registered_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_verified_author', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('avatar', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=True),
        sa.Column('role', sa.String(), server_default='user', nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # news
    op.create_table(
        'news',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('published_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('cover', sa.String(), nullable=True),
        sa.Column('author_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    )

    # comments
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('published_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('news_id', sa.Integer(), sa.ForeignKey('news.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    )

    # refresh_sessions
    op.create_table(
        'refresh_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    )
    op.create_index('ix_refresh_sessions_token', 'refresh_sessions', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_refresh_sessions_token', table_name='refresh_sessions')
    op.drop_table('refresh_sessions')
    op.drop_table('comments')
    op.drop_table('news')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
