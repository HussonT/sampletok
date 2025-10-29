#!/usr/bin/env python
"""Clean up duplicate TikTok URLs in the database, keeping only the most recent"""

import asyncio
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import Sample

async def cleanup_duplicates():
    """Remove duplicate samples, keeping only the most recent for each URL"""

    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # Find URLs that have duplicates
        subquery = (
            select(
                Sample.tiktok_url,
                func.count(Sample.id).label('count')
            )
            .group_by(Sample.tiktok_url)
            .having(func.count(Sample.id) > 1)
            .subquery()
        )

        # Get all duplicate URLs
        result = await db.execute(
            select(subquery.c.tiktok_url, subquery.c.count)
        )
        duplicate_urls = result.all()

        if not duplicate_urls:
            print("✅ No duplicate URLs found!")
            return

        print(f"Found {len(duplicate_urls)} URLs with duplicates:")

        for url, count in duplicate_urls:
            print(f"\n📍 URL: {url[:50]}... has {count} entries")

            # Get all samples for this URL, ordered by created_at
            query = select(Sample).where(
                Sample.tiktok_url == url
            ).order_by(Sample.created_at.desc())

            result = await db.execute(query)
            samples = result.scalars().all()

            # Keep the first (most recent) and delete the rest
            keep = samples[0]
            to_delete = samples[1:]

            print(f"  Keeping: {keep.id} (created: {keep.created_at}, status: {keep.status.value})")

            for sample in to_delete:
                print(f"  Deleting: {sample.id} (created: {sample.created_at}, status: {sample.status.value})")
                await db.delete(sample)

        await db.commit()
        print("\n✅ Cleanup completed!")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())