"""Add TimeRestriction columns and performance indexes

Revision ID: a1b2c3d4e5f6
Revises: 270b79a059e8
Create Date: 2026-08-11 09:43:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '270b79a059e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add TimeRestriction columns to rules table and performance indexes."""

    # --- Rules table: add new columns for TimeRestriction support ---
    # Make 'target' nullable (time rules don't have a target)
    op.alter_column('rules', 'target',
                    existing_type=sa.String(),
                    nullable=True)

    # Add new columns
    op.add_column('rules', sa.Column('daily_limit_minutes', sa.Integer(), nullable=True))
    op.add_column('rules', sa.Column('day_of_week', sa.Integer(), nullable=True))
    op.add_column('rules', sa.Column('allowed_start', sa.Time(), nullable=True))
    op.add_column('rules', sa.Column('allowed_end', sa.Time(), nullable=True))

    # --- Performance indexes ---
    op.create_index('ix_rules_device_id', 'rules', ['device_id'], unique=False)
    op.create_index('ix_alerts_device_id', 'alerts', ['device_id'], unique=False)
    op.create_index('ix_process_logs_device_id', 'process_logs', ['device_id'], unique=False)
    op.create_index('ix_process_logs_device_timestamp', 'process_logs', ['device_id', 'timestamp'], unique=False)


def downgrade() -> None:
    """Remove TimeRestriction columns and performance indexes."""

    # Drop indexes
    op.drop_index('ix_process_logs_device_timestamp', table_name='process_logs')
    op.drop_index('ix_process_logs_device_id', table_name='process_logs')
    op.drop_index('ix_alerts_device_id', table_name='alerts')
    op.drop_index('ix_rules_device_id', table_name='rules')

    # Drop columns
    op.drop_column('rules', 'allowed_end')
    op.drop_column('rules', 'allowed_start')
    op.drop_column('rules', 'day_of_week')
    op.drop_column('rules', 'daily_limit_minutes')

    # Revert target to non-nullable
    op.alter_column('rules', 'target',
                    existing_type=sa.String(),
                    nullable=False)
