"""drop_uix_doctor_start_time

Revision ID: 62582db1dd2d
Revises: 2847754a186b
Create Date: 2026-10-26 12:51:43.607484

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62582db1dd2d'
down_revision: Union[str, None] = '2847754a186b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Explicitly drop the exact index/constraint named in the error log
    op.execute("DROP INDEX IF EXISTS uix_doctor_start_time;")
    op.execute("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS uix_doctor_start_time;")


def downgrade() -> None:
    pass
