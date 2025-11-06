#!/usr/bin/env python3
"""
Backfill search_vector for existing samples

Run this AFTER the migration:
    python scripts/backfill_search_vectors.py

This script:
1. Updates search_vector for all samples without it
2. Creates the GIN index after backfill (much faster)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings


def create_index_concurrently():
    """
    Create GIN index using CONCURRENTLY to avoid table locks.

    CREATE INDEX CONCURRENTLY cannot run inside a transaction,
    so we use a synchronous connection with autocommit isolation.
    """
    # Convert asyncpg URL to psycopg2 URL
    sync_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')

    # Create synchronous engine with autocommit isolation
    sync_engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")

    try:
        with sync_engine.connect() as conn:
            # Check if index already exists
            index_exists = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = 'ix_samples_search_vector'
                )
            """)).scalar()

            if index_exists:
                print("✅ Index already exists!")
                return True

            print("Creating GIN index (this may take a while for large tables)...")
            conn.execute(text(
                "CREATE INDEX CONCURRENTLY ix_samples_search_vector ON samples USING GIN (search_vector)"
            ))
            print("✅ Index created successfully!")
            return True

    except Exception as e:
        print(f"❌ Error creating index: {e}")
        return False
    finally:
        sync_engine.dispose()


async def backfill_search_vectors():
    """Backfill search_vector for all samples and create index"""
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as session:
        # Count samples that need backfill
        count_query = text("SELECT COUNT(*) FROM samples WHERE search_vector IS NULL")
        result = await session.execute(count_query)
        total = result.scalar()

        print(f"Found {total} samples to backfill...")

        if total == 0:
            print("No samples to backfill. Checking if index exists...")
            # Create index using CONCURRENTLY (outside transaction)
            create_index_concurrently()
            return

        # Backfill search_vector
        print("Backfilling search_vector...")
        backfill_query = text("""
            UPDATE samples
            SET search_vector =
              setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
              setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
              setweight(to_tsvector('english', coalesce(creator_username, '')), 'C') ||
              setweight(to_tsvector('english', coalesce((SELECT string_agg(value, ' ') FROM jsonb_array_elements_text(tags)), '')), 'D')
            WHERE search_vector IS NULL
        """)

        await session.execute(backfill_query)
        await session.commit()

        print(f"✅ Backfilled {total} samples!")

    # Close async session and engine before creating index
    await engine.dispose()

    # Create GIN index AFTER backfill (much faster this way)
    # Uses CONCURRENTLY to avoid table locks
    create_index_concurrently()

    print("✅ Backfill complete!")


if __name__ == "__main__":
    asyncio.run(backfill_search_vectors())
