"""
Credit management service for atomic credit operations.

Provides thread-safe, database-level atomic operations for deducting
and refunding credits to prevent race conditions.
"""

import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select, and_
from app.models.user import User

logger = logging.getLogger(__name__)


async def deduct_credits_atomic(
    db: AsyncSession,
    user_id: UUID,
    credits_needed: int
) -> bool:
    """
    Atomically deduct credits from user account using database-level atomic operation.
    This prevents race conditions when multiple requests try to deduct credits simultaneously.

    Args:
        db: Database session
        user_id: UUID of the user
        credits_needed: Number of credits to deduct

    Returns:
        True if credits were successfully deducted, False if insufficient credits
    """
    result = await db.execute(
        update(User)
        .where(and_(
            User.id == user_id,
            User.credits >= credits_needed
        ))
        .values(credits=User.credits - credits_needed)
    )

    # If rowcount is 0, it means either user doesn't exist or insufficient credits
    if result.rowcount == 0:
        # Check if user exists to give better error message
        user_check = await db.execute(select(User).where(User.id == user_id))
        user = user_check.scalars().first()
        if not user:
            logger.error(f"User {user_id} not found during credit deduction")
            return False
        logger.warning(f"Insufficient credits for user {user_id}: has {user.credits}, needs {credits_needed}")
        return False

    await db.commit()
    logger.info(f"Atomically deducted {credits_needed} credits from user {user_id}")
    return True


async def refund_credits_atomic(
    db: AsyncSession,
    user_id: UUID,
    credits_to_refund: int
) -> None:
    """
    Atomically refund credits to user account.

    Args:
        db: Database session
        user_id: UUID of the user
        credits_to_refund: Number of credits to refund
    """
    if credits_to_refund <= 0:
        logger.warning(f"Attempted to refund {credits_to_refund} credits to user {user_id} - skipping")
        return

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(credits=User.credits + credits_to_refund)
    )
    await db.commit()
    logger.info(f"Refunded {credits_to_refund} credits to user {user_id}")


async def get_user_credits(db: AsyncSession, user_id: UUID) -> int:
    """
    Get current credit balance for a user.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Current credit balance, or 0 if user not found
    """
    result = await db.execute(select(User.credits).where(User.id == user_id))
    credits = result.scalar_one_or_none()
    return credits if credits is not None else 0
