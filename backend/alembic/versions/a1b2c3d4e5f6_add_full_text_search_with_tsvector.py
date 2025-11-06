"""add full-text search with tsvector

Revision ID: a1b2c3d4e5f6
Revises: fc13ea67ef28
Create Date: 2025-11-04 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fc13ea67ef28'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tsvector column (nullable, will be backfilled separately)
    op.add_column('samples', sa.Column('search_vector', TSVECTOR, nullable=True))

    # Create update function for trigger
    # Note: tags is a JSONB column, so we use jsonb_array_elements_text() to convert it
    op.execute('''
        CREATE FUNCTION update_search_vector() RETURNS trigger AS $$
        BEGIN
          NEW.search_vector :=
            setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(NEW.creator_username, '')), 'C') ||
            setweight(to_tsvector('english', coalesce((SELECT string_agg(value, ' ') FROM jsonb_array_elements_text(NEW.tags)), '')), 'D');
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')

    # Create trigger for future inserts/updates
    op.execute('''
        CREATE TRIGGER samples_search_vector_update
          BEFORE INSERT OR UPDATE ON samples
          FOR EACH ROW
          EXECUTE FUNCTION update_search_vector();
    ''')


def downgrade() -> None:
    op.execute('DROP TRIGGER IF EXISTS samples_search_vector_update ON samples')
    op.execute('DROP FUNCTION IF EXISTS update_search_vector()')
    op.drop_column('samples', 'search_vector')
