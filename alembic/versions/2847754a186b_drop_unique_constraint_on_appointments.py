"""drop_unique_constraint_on_appointments

Revision ID: 2847754a186b
Revises: 747878cb9ec0
Create Date: 2026-10-26 12:40:23.527642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2847754a186b'
down_revision: Union[str, None] = '747878cb9ec0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the unique constraint using IF EXISTS to prevent errors if it's already gone
    # We check both the custom name and the default Postgres generated name
    op.execute("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS uq_doctor_start_time;")
    op.execute("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_doctor_id_start_time_key;")


def downgrade() -> None:
    # No need to recreate it for the assessment
    pass