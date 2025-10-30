#!/usr/bin/env python3
"""
Admin script to reset stuck collection in production
Run this locally with: source venv/bin/activate && python admin_reset_collection.py
"""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Use production DATABASE_URL (will be fetched from gcloud)
DATABASE_URL = os.popen('gcloud secrets versions access latest --secret="DATABASE_URL" --project=sampletok').read().strip()

# Modify for Cloud SQL Proxy connection
# Replace Unix socket with TCP connection for local access
if '/cloudsql/' in DATABASE_URL:
    # Extract the connection details
    parts = DATABASE_URL.split('@')
    credentials = parts[0].replace('postgresql+asyncpg://', '')
    socket_path = parts[1].split('/')[0]
    db_name = parts[1].split('/')[-1]

    # Use localhost with Cloud SQL Proxy (you need to start it first)
    DATABASE_URL = f"postgresql+asyncpg://{credentials}@localhost:5432/{db_name}"
    print("⚠️  Using Cloud SQL Proxy connection.")
    print("   Make sure Cloud SQL Proxy is running:")
    print("   cloud-sql-proxy sampletok:us-central1:sampletok-db --port 5432")
    print()

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def reset_collection():
    collection_id = "2a3960d1-f762-4947-8f50-f2a736dd1bf6"

    print(f"Resetting collection {collection_id}...\n")

    async with AsyncSessionLocal() as db:
        # Get collection details
        result = await db.execute(text("""
            SELECT
                c.name,
                c.status,
                c.total_video_count,
                COALESCE(c.processed_count, 0) as processed_count,
                c.total_video_count - COALESCE(c.processed_count, 0) as credits_to_refund,
                u.email,
                u.credits as current_credits
            FROM collections c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = :collection_id
        """), {"collection_id": collection_id})

        row = result.first()
        if not row:
            print(f"❌ Collection {collection_id} not found")
            return

        print(f"Collection: {row.name}")
        print(f"User: {row.email}")
        print(f"Status: {row.status}")
        print(f"Videos processed: {row.processed_count}/{row.total_video_count}")
        print(f"Current credits: {row.current_credits}")
        print(f"Credits to refund: {row.credits_to_refund}")
        print()

        # Confirm
        confirm = input("Proceed with reset and refund? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return

        # Execute reset
        await db.execute(text("""
            WITH refund_calc AS (
                SELECT user_id, total_video_count - COALESCE(processed_count, 0) as refund
                FROM collections
                WHERE id = :collection_id
            )
            UPDATE users
            SET credits = credits + (SELECT refund FROM refund_calc)
            WHERE id = (SELECT user_id FROM refund_calc)
        """), {"collection_id": collection_id})

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
        result2 = await db.execute(text("""
            SELECT u.credits
            FROM users u
            JOIN collections c ON c.user_id = u.id
            WHERE c.id = :collection_id
        """), {"collection_id": collection_id})
        new_credits = result2.scalar()

        print()
        print(f"✅ Collection reset to 'pending' status!")
        print(f"✅ Refunded {row.credits_to_refund} credits")
        print(f"✅ New credit balance: {new_credits}")
        print()
        print("The collection can now be reprocessed (Inngest functions are now synced!)")

if __name__ == "__main__":
    try:
        asyncio.run(reset_collection())
    except KeyboardInterrupt:
        print("\nCancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Cloud SQL Proxy is running:")
        print("  cloud-sql-proxy sampletok:us-central1:sampletok-db --port 5432")
