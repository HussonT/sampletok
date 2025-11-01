"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

⚠️ MIGRATION CHECKLIST - DELETE THIS BEFORE COMMITTING ⚠️
═══════════════════════════════════════════════════════════
Before committing, verify:
  ✓ ONLY schema changes (DDL: CREATE, ALTER, DROP)
  ✓ NO data operations (DML: UPDATE, INSERT, DELETE)
  ✓ NO op.execute() with UPDATE/INSERT/DELETE
  ✓ Can run safely on empty database
  ✓ Tested: alembic upgrade head && alembic downgrade -1

Need to modify data? Use backend/scripts/sql/ instead!
See: backend/alembic/MIGRATION_GUIDELINES.md
═══════════════════════════════════════════════════════════

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}