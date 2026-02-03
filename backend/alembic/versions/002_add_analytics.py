"""Add analytics tables

Revision ID: 002_add_analytics
Revises: 001_initial
Create Date: 2026-01-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_analytics'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create query_logs table
    op.create_table(
        'query_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('sources_count', sa.Integer(), nullable=True, default=0),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('was_cached', sa.Boolean(), nullable=True, default=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_query_logs_session_id', 'query_logs', ['session_id'])
    op.create_index('ix_query_logs_created_at', 'query_logs', ['created_at'])

    # Create daily_stats table
    op.create_table(
        'daily_stats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_queries', sa.Integer(), nullable=True, default=0),
        sa.Column('unique_users', sa.Integer(), nullable=True, default=0),
        sa.Column('total_sessions', sa.Integer(), nullable=True, default=0),
        sa.Column('avg_response_time_ms', sa.Float(), nullable=True),
        sa.Column('cached_queries', sa.Integer(), nullable=True, default=0),
        sa.Column('failed_queries', sa.Integer(), nullable=True, default=0),
        sa.Column('total_tokens_used', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index('ix_daily_stats_date', 'daily_stats', ['date'])

    # Create user_activity table
    op.create_table(
        'user_activity',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('extra_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_activity_created_at', 'user_activity', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_user_activity_created_at', table_name='user_activity')
    op.drop_table('user_activity')
    
    op.drop_index('ix_daily_stats_date', table_name='daily_stats')
    op.drop_table('daily_stats')
    
    op.drop_index('ix_query_logs_created_at', table_name='query_logs')
    op.drop_index('ix_query_logs_session_id', table_name='query_logs')
    op.drop_table('query_logs')
