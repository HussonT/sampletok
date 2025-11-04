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

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings


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

            # Check if index exists
            index_check = text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = 'ix_samples_search_vector'
                )
            """)
            index_exists = await session.scalar(index_check)

            if not index_exists:
                print("Creating GIN index...")
                await session.execute(text(
                    "CREATE INDEX ix_samples_search_vector ON samples USING GIN (search_vector)"
                ))
                await session.commit()
                print("✅ Index created!")
            else:
                print("✅ Index already exists!")

            return

        # Backfill search_vector
        print("Backfilling search_vector...")
        backfill_query = text("""
            UPDATE samples
            SET search_vector =
              setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
              setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
              setweight(to_tsvector('english', coalesce(creator_username, '')), 'C') ||
              setweight(to_tsvector('english', coalesce(array_to_string(tags, ' '), '')), 'D')
            WHERE search_vector IS NULL
        """)

        await session.execute(backfill_query)
        await session.commit()

        print(f"✅ Backfilled {total} samples!")

        # Create GIN index AFTER backfill (much faster this way)
        print("Creating GIN index...")
        await session.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_samples_search_vector ON samples USING GIN (search_vector)"
        ))
        await session.commit()

        print("✅ Index created!")
        print("✅ Backfill complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(backfill_search_vectors())
