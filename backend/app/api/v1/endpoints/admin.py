"""
Admin endpoints for emergency operations
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.core.config import settings
from app.models import Collection, CollectionStatus, User

logger = logging.getLogger(__name__)

router = APIRouter()


class AddCreditsRequest(BaseModel):
    clerk_id: str
    credits: int

    class Config:
        json_schema_extra = {
            "example": {
                "clerk_id": "user_2abc123def456",
                "credits": 100
            }
        }


@router.post("/reset-user-collections")
async def reset_user_collections(
    email: str,
    x_admin_key: str = Header(..., description="Admin API key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Emergency endpoint to reset all stuck collections for a user and refund credits.

    Requires X-Admin-Key header matching SECRET_KEY for security.
    """
    # Verify admin key
    if x_admin_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    logger.info(f"Admin: Resetting collections for user {email}")

    # Get user
    user_query = select(User).where(User.email == email)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {email} not found")

    # Get stuck collections
    collections_query = select(Collection).where(
        Collection.user_id == user.id,
        Collection.status.in_([CollectionStatus.pending, CollectionStatus.processing, CollectionStatus.failed])
    )
    collections_result = await db.execute(collections_query)
    stuck_collections = collections_result.scalars().all()

    if not stuck_collections:
        return {
            "message": "No stuck collections found",
            "user_email": email,
            "collections_reset": 0,
            "credits_refunded": 0,
            "current_credits": user.credits
        }

    # Calculate total refund
    total_refund = sum(
        (c.total_video_count - (c.processed_count or 0))
        for c in stuck_collections
    )

    # Refund credits
    user.credits += total_refund

    # Reset collections
    reset_details = []
    for collection in stuck_collections:
        videos_to_refund = collection.total_video_count - (collection.processed_count or 0)
        reset_details.append({
            "id": str(collection.id),
            "name": collection.name,
            "status": collection.status.value,
            "videos_processed": collection.processed_count or 0,
            "total_videos": collection.total_video_count,
            "credits_refunded": videos_to_refund
        })

        collection.status = CollectionStatus.pending
        collection.processed_count = 0
        collection.error_message = None
        collection.current_cursor = 0
        collection.started_at = None
        collection.completed_at = None

    await db.commit()

    logger.info(
        f"Admin: Reset {len(stuck_collections)} collections for {email}, "
        f"refunded {total_refund} credits, new balance: {user.credits}"
    )

    return {
        "message": f"Successfully reset {len(stuck_collections)} collections",
        "user_email": email,
        "collections_reset": len(stuck_collections),
        "credits_refunded": total_refund,
        "current_credits": user.credits,
        "collections": reset_details
    }


@router.post("/reset-collection/{collection_id}")
async def reset_collection_by_id(
    collection_id: str,
    x_admin_key: str = Header(..., description="Admin API key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Emergency endpoint to reset a specific collection and refund credits.

    Requires X-Admin-Key header matching SECRET_KEY for security.

    Example:
        POST /api/v1/admin/reset-collection/2a3960d1-f762-4947-8f50-f2a736dd1bf6
        X-Admin-Key: your-secret-key
    """
    # Verify admin key
    if x_admin_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    logger.info(f"Admin: Resetting collection {collection_id}")

    # Get collection
    collection_query = select(Collection).where(Collection.id == text(f"'{collection_id}'::uuid"))
    collection_result = await db.execute(collection_query)
    collection = collection_result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection {collection_id} not found")

    # Get user
    user_query = select(User).where(User.id == collection.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found for collection")

    # Calculate refund
    videos_to_refund = collection.total_video_count - (collection.processed_count or 0)

    # Store old state
    old_status = collection.status.value
    old_credits = user.credits

    # Refund credits
    if videos_to_refund > 0:
        user.credits += videos_to_refund

    # Reset collection
    collection.status = CollectionStatus.pending
    collection.processed_count = 0
    collection.error_message = None
    collection.current_cursor = 0
    collection.started_at = None
    collection.completed_at = None

    await db.commit()

    logger.info(
        f"Admin: Reset collection {collection_id} (status: {old_status} → pending), "
        f"refunded {videos_to_refund} credits to user {user.clerk_user_id}, "
        f"balance: {old_credits} → {user.credits}"
    )

    return {
        "message": "Successfully reset collection",
        "collection_id": collection_id,
        "collection_name": collection.name,
        "old_status": old_status,
        "new_status": "pending",
        "user_clerk_id": user.clerk_user_id,
        "user_email": user.email,
        "credits_refunded": videos_to_refund,
        "previous_balance": old_credits,
        "new_balance": user.credits,
        "total_videos": collection.total_video_count,
        "videos_processed": 0
    }


@router.post("/add-credits")
async def add_credits(
    request: AddCreditsRequest,
    x_admin_key: str = Header(..., description="Admin API key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Add credits to a user's account by their Clerk ID.

    Requires X-Admin-Key header matching SECRET_KEY for security.

    Example:
        POST /api/v1/admin/add-credits
        X-Admin-Key: your-secret-key
        {
            "clerk_id": "user_2abc123def456",
            "credits": 100
        }
    """
    # Verify admin key
    if x_admin_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    if request.credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")

    logger.info(f"Admin: Adding {request.credits} credits to Clerk ID {request.clerk_id}")

    # Find user by Clerk ID
    user_query = select(User).where(User.clerk_user_id == request.clerk_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with Clerk ID {request.clerk_id} not found"
        )

    # Store old balance
    old_credits = user.credits

    # Add credits
    user.credits += request.credits
    await db.commit()

    logger.info(
        f"Admin: Added {request.credits} credits to user {user.clerk_user_id}. "
        f"Balance: {old_credits} → {user.credits}"
    )

    return {
        "message": f"Successfully added {request.credits} credits",
        "user_email": user.email,
        "clerk_id": user.clerk_user_id,
        "credits_added": request.credits,
        "previous_balance": old_credits,
        "new_balance": user.credits
    }
