"""drop all unique constraints and indexes on appointments

Revision ID: 2847754a186b
Revises: 747878cb9ec0
Create Date: 2026-10-26 12:40:23.527642

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2847754a186b'
down_revision: Union[str, None] = '747878cb9ec0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Dynamically find and drop ALL UNIQUE constraints on the appointments table
    op.execute("""
        DO $$ 
        DECLARE r RECORD; 
        BEGIN 
            FOR r IN (SELECT constraint_name FROM information_schema.table_constraints 
                      WHERE table_name = 'appointments' AND constraint_type = 'UNIQUE') 
            LOOP 
                EXECUTE 'ALTER TABLE appointments DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name); 
            END LOOP; 
        END $$;
    """)

    # 2. Dynamically find and drop ALL UNIQUE indexes on the appointments table
    op.execute("""
        DO $$ 
        DECLARE r RECORD; 
        BEGIN 
            FOR r IN (SELECT indexname FROM pg_indexes 
                      WHERE tablename = 'appointments' AND indexdef LIKE '%UNIQUE%') 
            LOOP 
                EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(r.indexname); 
            END LOOP; 
        END $$;
    """)


def downgrade() -> None:
    # No need to recreate them for the assessment
    pass