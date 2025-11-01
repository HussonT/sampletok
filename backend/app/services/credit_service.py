"""
Credit management service for atomic credit operations with subscription support.

Provides thread-safe, database-level atomic operations for:
- Adding credits (with idempotency for webhooks)
- Deducting credits (atomic with transaction audit)
- Refunding credits
- Checking subscription + credit eligibility

All operations create CreditTransaction records for complete audit trail.
"""

import logging
from typing import Optional, Dict, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select, and_
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.credit_transaction import CreditTransaction
from app.models.subscription import Subscription
from app.utils import utcnow_naive

logger = logging.getLogger(__name__)


class CreditService:
    """Service for managing user credits with full audit trail."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_credits_atomic(
        self,
        user_id: UUID,
        credits: int,
        transaction_type: str,
        description: str,
        subscription_id: Optional[UUID] = None,
        stripe_invoice_id: Optional[str] = None,
        stripe_session_id: Optional[str] = None,
        stripe_payment_intent_id: Optional[str] = None,
        top_up_package: Optional[str] = None,
        discount_applied: Optional[float] = None,
        amount_cents: Optional[int] = None
    ) -> Dict:
        """
        Add credits atomically with database locking and idempotency.

        CRITICAL: This method MUST be idempotent to handle duplicate webhooks!

        Args:
            user_id: UUID of the user
            credits: Number of credits to add (positive integer)
            transaction_type: Type of transaction (subscription_grant, monthly_renewal, top_up_purchase, etc.)
            description: Human-readable description
            subscription_id: Optional subscription reference
            stripe_invoice_id: For idempotency - prevents duplicate processing of same invoice
            stripe_session_id: For idempotency - prevents duplicate processing of same checkout session
            stripe_payment_intent_id: For idempotency - prevents duplicate processing of same payment
            top_up_package: Package size (small, medium, large)
            discount_applied: Discount percentage applied
            amount_cents: Amount paid in cents

        Returns:
            {
                "duplicate": bool,  # True if this was a duplicate webhook
                "transaction_id": str,
                "previous_balance": int,
                "credits_added": int,
                "new_balance": int
            }

        Raises:
            ValueError: If credits would result in negative balance
            IntegrityError: If database constraint violated
        """
        async with self.db.begin_nested():  # Creates savepoint for rollback
            try:
                # 🔒 LOCK: Acquire row-level lock on user
                # Prevents concurrent modifications to same user's credits
                result = await self.db.execute(
                    select(User)
                    .where(User.id == user_id)
                    .with_for_update()  # SELECT FOR UPDATE
                )
                user = result.scalar_one_or_none()

                if not user:
                    from app.exceptions import BusinessLogicError
                    raise BusinessLogicError(
                        f"User not found: {user_id}. Cannot add credits to non-existent user.",
                        details={"user_id": str(user_id)}
                    )

                # 🔍 IDEMPOTENCY CHECK: Has this exact transaction been processed?
                if stripe_invoice_id:
                    existing = await self.db.execute(
                        select(CreditTransaction)
                        .where(
                            CreditTransaction.user_id == user_id,
                            CreditTransaction.stripe_invoice_id == stripe_invoice_id,
                            CreditTransaction.transaction_type == transaction_type,
                            CreditTransaction.status == 'completed'
                        )
                    )
                    existing_tx = existing.scalar_one_or_none()

                    if existing_tx:
                        logger.info(
                            f"⚠️ DUPLICATE WEBHOOK: Invoice {stripe_invoice_id} already processed. "
                            f"Skipping credit grant. Transaction ID: {existing_tx.id}"
                        )
                        return {
                            "duplicate": True,
                            "transaction_id": str(existing_tx.id),
                            "previous_balance": existing_tx.previous_balance,
                            "credits_added": 0,
                            "new_balance": existing_tx.new_balance
                        }

                # Check for duplicate checkout sessions (top-up purchases)
                if stripe_session_id:
                    existing = await self.db.execute(
                        select(CreditTransaction)
                        .where(
                            CreditTransaction.user_id == user_id,
                            CreditTransaction.stripe_session_id == stripe_session_id,
                            CreditTransaction.status == 'completed'
                        )
                    )
                    existing_tx = existing.scalar_one_or_none()

                    if existing_tx:
                        logger.info(f"⚠️ DUPLICATE: Checkout session {stripe_session_id} already processed.")
                        return {
                            "duplicate": True,
                            "transaction_id": str(existing_tx.id),
                            "previous_balance": existing_tx.previous_balance,
                            "credits_added": 0,
                            "new_balance": existing_tx.new_balance
                        }

                # Same check for payment intents (top-up purchases)
                if stripe_payment_intent_id:
                    existing = await self.db.execute(
                        select(CreditTransaction)
                        .where(
                            CreditTransaction.user_id == user_id,
                            CreditTransaction.stripe_payment_intent_id == stripe_payment_intent_id,
                            CreditTransaction.status == 'completed'
                        )
                    )
                    existing_tx = existing.scalar_one_or_none()

                    if existing_tx:
                        logger.info(f"⚠️ DUPLICATE: Payment intent {stripe_payment_intent_id} already processed.")
                        return {
                            "duplicate": True,
                            "transaction_id": str(existing_tx.id),
                            "previous_balance": existing_tx.previous_balance,
                            "credits_added": 0,
                            "new_balance": existing_tx.new_balance
                        }

                # 💰 PERFORM CREDIT OPERATION
                previous_balance = user.credits
                new_balance = previous_balance + credits

                # Sanity check
                if new_balance < 0:
                    logger.error(
                        f"❌ Attempted negative balance: user={user_id}, "
                        f"previous={previous_balance}, adding={credits}"
                    )
                    raise ValueError("Credit balance cannot be negative")

                user.credits = new_balance

                # 📝 CREATE AUDIT RECORD
                transaction = CreditTransaction(
                    user_id=user_id,
                    subscription_id=subscription_id,
                    transaction_type=transaction_type,
                    credits_amount=credits,
                    previous_balance=previous_balance,
                    new_balance=new_balance,
                    description=description,
                    stripe_invoice_id=stripe_invoice_id,
                    stripe_session_id=stripe_session_id,
                    stripe_payment_intent_id=stripe_payment_intent_id,
                    top_up_package=top_up_package,
                    discount_applied=discount_applied,
                    amount_cents=amount_cents,
                    status='completed',
                    completed_at=utcnow_naive()
                )

                self.db.add(transaction)
                await self.db.flush()  # Write to DB but don't commit yet

                logger.info(
                    f"✅ Credits added: user={user_id}, amount={credits}, "
                    f"balance: {previous_balance} → {new_balance}, type={transaction_type}"
                )

                return {
                    "duplicate": False,
                    "transaction_id": str(transaction.id),
                    "previous_balance": previous_balance,
                    "credits_added": credits,
                    "new_balance": new_balance
                }

            except IntegrityError as e:
                logger.error(f"❌ Integrity error in credit operation: {e}")
                await self.db.rollback()
                raise
            except Exception as e:
                logger.error(f"❌ Error adding credits: {e}")
                await self.db.rollback()
                raise

    async def deduct_credits_atomic(
        self,
        user_id: UUID,
        credits_needed: int,
        transaction_type: str = "deduction",
        description: Optional[str] = None,
        collection_id: Optional[UUID] = None,
        sample_id: Optional[UUID] = None
    ) -> bool:
        """
        Atomically deduct credits from user account using database-level atomic operation.
        This prevents race conditions when multiple requests try to deduct credits simultaneously.

        Creates CreditTransaction record for audit trail.

        Args:
            user_id: UUID of the user
            credits_needed: Number of credits to deduct
            transaction_type: Type of transaction (default: "deduction")
            description: Optional description of the deduction
            collection_id: Optional collection reference
            sample_id: Optional sample reference

        Returns:
            True if credits were successfully deducted, False if insufficient credits
        """
        async with self.db.begin_nested():
            try:
                # Lock user row
                result = await self.db.execute(
                    select(User)
                    .where(User.id == user_id)
                    .with_for_update()
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.error(f"User {user_id} not found during credit deduction")
                    return False

                # Check sufficient credits
                if user.credits < credits_needed:
                    logger.warning(
                        f"Insufficient credits for user {user_id}: has {user.credits}, needs {credits_needed}"
                    )
                    return False

                # Deduct credits
                previous_balance = user.credits
                new_balance = previous_balance - credits_needed
                user.credits = new_balance

                # Create transaction record
                transaction = CreditTransaction(
                    user_id=user_id,
                    transaction_type=transaction_type,
                    credits_amount=-credits_needed,  # Negative for deduction
                    previous_balance=previous_balance,
                    new_balance=new_balance,
                    description=description or f"Deducted {credits_needed} credits",
                    collection_id=collection_id,
                    sample_id=sample_id,
                    status='completed',
                    completed_at=utcnow_naive()
                )

                self.db.add(transaction)
                await self.db.flush()

                logger.info(f"Atomically deducted {credits_needed} credits from user {user_id}")
                return True

            except Exception as e:
                logger.error(f"Error deducting credits: {e}")
                await self.db.rollback()
                raise

    async def refund_credits_atomic(
        self,
        user_id: UUID,
        credits_to_refund: int,
        description: Optional[str] = None,
        collection_id: Optional[UUID] = None,
        sample_id: Optional[UUID] = None
    ) -> None:
        """
        Atomically refund credits to user account.

        Creates CreditTransaction record for audit trail.

        Args:
            user_id: UUID of the user
            credits_to_refund: Number of credits to refund
            description: Optional description of the refund
            collection_id: Optional collection reference
            sample_id: Optional sample reference
        """
        if credits_to_refund <= 0:
            logger.warning(f"Attempted to refund {credits_to_refund} credits to user {user_id} - skipping")
            return

        async with self.db.begin_nested():
            try:
                # Lock user row
                result = await self.db.execute(
                    select(User)
                    .where(User.id == user_id)
                    .with_for_update()
                )
                user = result.scalar_one()

                # Refund credits
                previous_balance = user.credits
                new_balance = previous_balance + credits_to_refund
                user.credits = new_balance

                # Create transaction record
                transaction = CreditTransaction(
                    user_id=user_id,
                    transaction_type="refund",
                    credits_amount=credits_to_refund,
                    previous_balance=previous_balance,
                    new_balance=new_balance,
                    description=description or f"Refunded {credits_to_refund} credits",
                    collection_id=collection_id,
                    sample_id=sample_id,
                    status='completed',
                    completed_at=utcnow_naive()
                )

                self.db.add(transaction)
                await self.db.flush()

                logger.info(f"Refunded {credits_to_refund} credits to user {user_id}")

            except Exception as e:
                logger.error(f"Error refunding credits: {e}")
                await self.db.rollback()
                raise

    async def get_user_credits(self, user_id: UUID) -> int:
        """
        Get current credit balance for a user.

        Args:
            user_id: UUID of the user

        Returns:
            Current credit balance, or 0 if user not found
        """
        result = await self.db.execute(select(User.credits).where(User.id == user_id))
        credits = result.scalar_one_or_none()
        return credits if credits is not None else 0

    async def can_process_collection(
        self,
        user_id: UUID,
        video_count: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user can process a collection.
        Requires active subscription AND sufficient credits.

        Args:
            user_id: UUID of the user
            video_count: Number of videos to process

        Returns:
            Tuple of (can_process: bool, error_message: Optional[str])
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return False, "User not found"

        # Load subscription relationship
        await self.db.refresh(user, ["subscription"])

        # Check subscription
        if not user.subscription:
            return False, "Active subscription required to process collections. Please subscribe to continue."

        if not user.subscription.is_active:
            status = user.subscription.status
            if status == "cancelled":
                return False, "Your subscription has been cancelled. Please renew to continue processing."
            elif status == "past_due":
                return False, "Your subscription payment is past due. Please update your payment method."
            else:
                return False, f"Active subscription required (current status: {status})"

        # Check credits
        if user.credits < video_count:
            return False, f"Insufficient credits. You need {video_count} credits but only have {user.credits}. Consider purchasing a top-up or upgrading your plan."

        return True, None


# Legacy function wrappers for backwards compatibility
async def deduct_credits_atomic(db: AsyncSession, user_id: UUID, credits_needed: int) -> bool:
    """Legacy wrapper - use CreditService.deduct_credits_atomic() instead"""
    service = CreditService(db)
    return await service.deduct_credits_atomic(user_id, credits_needed)


async def refund_credits_atomic(db: AsyncSession, user_id: UUID, credits_to_refund: int) -> None:
    """Legacy wrapper - use CreditService.refund_credits_atomic() instead"""
    service = CreditService(db)
    await service.refund_credits_atomic(user_id, credits_to_refund)


async def get_user_credits(db: AsyncSession, user_id: UUID) -> int:
    """Legacy wrapper - use CreditService.get_user_credits() instead"""
    service = CreditService(db)
    return await service.get_user_credits(user_id)
