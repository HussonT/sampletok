#!/bin/bash
# Quick fix for stuck collection - run this script directly on Cloud Run

COLLECTION_ID="2a3960d1-f762-4947-8f50-f2a736dd1bf6"

# This script uses the backend's internal Python environment
cat << 'PYTHON_SCRIPT' > /tmp/fix_collection.py
import asyncio
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models import Collection, CollectionStatus

async def fix_collection():
    collection_id = "2a3960d1-f762-4947-8f50-f2a736dd1bf6"

    async with AsyncSessionLocal() as db:
        # Get collection and calculate refund
        result = await db.execute(text("""
            SELECT
                c.user_id,
                c.name,
                c.status,
                c.total_video_count,
                COALESCE(c.processed_count, 0) as processed_count,
                c.total_video_count - COALESCE(c.processed_count, 0) as credits_to_refund,
                u.credits as current_credits
            FROM collections c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = :collection_id
        """), {"collection_id": collection_id})

        row = result.first()
        if not row:
            print(f"Collection {collection_id} not found")
            return

        print(f"Collection: {row.name}")
        print(f"Status: {row.status}")
        print(f"Videos: {row.processed_count}/{row.total_video_count}")
        print(f"User credits before: {row.current_credits}")
        print(f"Credits to refund: {row.credits_to_refund}")

        # Refund credits
        await db.execute(text("""
            UPDATE users
            SET credits = credits + :refund
            WHERE id = :user_id
        """), {"refund": row.credits_to_refund, "user_id": row.user_id})

        # Reset collection
        await db.execute(text("""
            UPDATE collections
            SET status = 'pending',
                processed_count = 0,
                error_message = NULL,
                current_cursor = 0,
                started_at = NULL,
                completed_at = NULL
            WHERE id = :collection_id
        """), {"collection_id": collection_id})

        await db.commit()

        # Get new balance
        result2 = await db.execute(text("SELECT credits FROM users WHERE id = :user_id"), {"user_id": row.user_id})
        new_credits = result2.scalar()

        print(f"\n✅ Collection reset!")
        print(f"✅ Refunded {row.credits_to_refund} credits")
        print(f"User credits after: {new_credits}")

if __name__ == "__main__":
    asyncio.run(fix_collection())
PYTHON_SCRIPT

# Run the Python script
python /tmp/fix_collection.py
