#!/usr/bin/env python3
"""
Quick script to reset a stuck collection and refund credits
"""
import asyncio
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Collection, CollectionStatus, User
from app.services.credit_service import refund_credits_atomic

async def reset_collection(collection_id: str):
    async with AsyncSessionLocal() as db:
        # Get the collection
        query = select(Collection).where(Collection.id == collection_id)
        result = await db.execute(query)
        collection = result.scalar_one_or_none()

        if not collection:
            print(f"❌ Collection {collection_id} not found")
            return

        print(f"Found collection: {collection.name}")
        print(f"Status: {collection.status.value}")
        print(f"Total videos: {collection.total_video_count}")
        print(f"Processed: {collection.processed_count or 0}")

        # Calculate refund
        total_videos = collection.total_video_count
        processed_videos = collection.processed_count or 0
        videos_to_refund = total_videos - processed_videos

        print(f"\nCredits to refund: {videos_to_refund}")

        if videos_to_refund > 0:
            # Refund credits
            await refund_credits_atomic(db, collection.user_id, videos_to_refund)
            print(f"✅ Refunded {videos_to_refund} credits to user")

        # Reset collection
        collection.status = CollectionStatus.pending
        collection.processed_count = 0
        collection.error_message = None
        collection.current_cursor = 0
        collection.started_at = None
        collection.completed_at = None

        await db.commit()
        print(f"✅ Collection reset to pending status")

        # Get user's new credit balance
        user_query = select(User).where(User.id == collection.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one()
        print(f"\nUser's current credit balance: {user.credits}")

if __name__ == "__main__":
    collection_id = "2a3960d1-f762-4947-8f50-f2a736dd1bf6"
    print(f"Resetting collection {collection_id}...\n")
    asyncio.run(reset_collection(collection_id))
