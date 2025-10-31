"""
Subscription management service for handling Stripe subscriptions.

Manages the complete subscription lifecycle including:
- Creating Stripe Checkout sessions
- Handling webhook events (created, updated, deleted)
- Managing subscription status and tier changes
- Coordinating credit grants with subscription events
"""

import logging
import stripe
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.user import User
from app.models.subscription import Subscription
from app.models.stripe_customer import StripeCustomer
from app.models.credit_transaction import CreditTransaction

# Initialize Stripe with secret key
if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Manages subscription lifecycle and Stripe subscription operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_tier_credits(self, tier: str) -> int:
        """Get monthly credit allowance for a tier from config."""
        tier_map = {
            "basic": settings.TIER_CREDITS_BASIC,
            "pro": settings.TIER_CREDITS_PRO,
            "ultimate": settings.TIER_CREDITS_ULTIMATE
        }
        return tier_map.get(tier, 0)

    def _get_tier_discount(self, tier: str) -> float:
        """Get top-up discount percentage for a tier from config."""
        tier_map = {
            "basic": settings.TIER_DISCOUNT_BASIC,
            "pro": settings.TIER_DISCOUNT_PRO,
            "ultimate": settings.TIER_DISCOUNT_ULTIMATE
        }
        return tier_map.get(tier, 0.0)

    async def create_checkout_session(
        self,
        user: User,
        price_id: str,
        tier: str,
        billing_interval: str
    ) -> Dict[str, str]:
        """
        Create Stripe Checkout session for new subscription.

        Args:
            user: User subscribing
            price_id: Stripe price ID for the selected plan
            tier: Subscription tier (basic, pro, ultimate)
            billing_interval: Billing interval (month, year)

        Returns:
            {
                "session_id": "cs_xxx",
                "checkout_url": "https://checkout.stripe.com/..."
            }

        Raises:
            ValueError: If user already has active subscription
            RuntimeError: If Stripe API call fails
        """
        # Check if user already has active subscription
        existing_sub = await self.get_user_subscription(user.id)
        if existing_sub and existing_sub.is_active:
            raise ValueError("User already has an active subscription. Please cancel before subscribing again.")

        # Get or create Stripe customer
        stripe_customer = await self._get_or_create_stripe_customer(user)

        # Prepare checkout session parameters
        session_params = {
            "customer": stripe_customer.stripe_customer_id,
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            "mode": "subscription",
            "success_url": f"{settings.SUBSCRIPTION_SUCCESS_URL}?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": settings.SUBSCRIPTION_CANCEL_URL,
            "metadata": {
                "user_id": str(user.id),
                "tier": tier,
                "billing_interval": billing_interval
            },
            "subscription_data": {
                "metadata": {
                    "user_id": str(user.id),
                    "tier": tier
                }
            }
        }

        try:
            session = stripe.checkout.Session.create(**session_params)
            logger.info(f"Created checkout session {session.id} for user {user.id}")

            return {
                "session_id": session.id,
                "checkout_url": session.url
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise RuntimeError(f"Failed to create checkout session: {str(e)}")

    async def get_user_subscription(self, user_id: UUID) -> Optional[Subscription]:
        """
        Get user's current subscription.

        Args:
            user_id: UUID of the user

        Returns:
            Subscription object or None if no subscription exists
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def cancel_subscription(
        self,
        user_id: UUID,
        cancel_at_period_end: bool = True
    ) -> Subscription:
        """
        Cancel user's subscription.

        Args:
            user_id: UUID of the user
            cancel_at_period_end: If True, cancel at end of billing period (grace period).
                                 If False, cancel immediately.

        Returns:
            Updated Subscription object

        Raises:
            ValueError: If no active subscription found
            RuntimeError: If Stripe API call fails
        """
        subscription = await self.get_user_subscription(user_id)

        if not subscription:
            raise ValueError("No subscription found for user")

        if not subscription.is_active:
            raise ValueError("Subscription is not active")

        try:
            if cancel_at_period_end:
                # Schedule cancellation at period end (user keeps access)
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                subscription.cancel_at_period_end = True
                logger.info(f"Scheduled cancellation for subscription {subscription.id} at period end")
            else:
                # Cancel immediately
                stripe.Subscription.cancel(subscription.stripe_subscription_id)
                subscription.status = "cancelled"
                subscription.cancelled_at = datetime.utcnow()
                logger.info(f"Immediately cancelled subscription {subscription.id}")

            await self.db.commit()
            await self.db.refresh(subscription)

            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error cancelling subscription: {e}")
            raise RuntimeError(f"Failed to cancel subscription: {str(e)}")

    async def change_tier(
        self,
        user_id: UUID,
        new_price_id: str,
        new_tier: str
    ) -> Subscription:
        """
        Change subscription tier (upgrade or downgrade).

        Args:
            user_id: UUID of the user
            new_price_id: Stripe price ID for new tier
            new_tier: New tier name (basic, pro, ultimate)

        Returns:
            Updated Subscription object

        Raises:
            ValueError: If no active subscription found or same tier
            RuntimeError: If Stripe API call fails
        """
        subscription = await self.get_user_subscription(user_id)

        if not subscription:
            raise ValueError("No subscription found for user")

        if not subscription.is_active:
            raise ValueError("Subscription is not active")

        if subscription.tier == new_tier:
            raise ValueError("Already subscribed to this tier")

        try:
            # Get current Stripe subscription
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)

            # Update the subscription item with new price
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    "id": stripe_sub["items"]["data"][0].id,
                    "price": new_price_id,
                }],
                metadata={
                    "user_id": str(user_id),
                    "tier": new_tier
                },
                proration_behavior="always_invoice"  # Charge immediately for upgrade
            )

            # Update local subscription record
            old_tier = subscription.tier
            subscription.tier = new_tier
            subscription.stripe_price_id = new_price_id
            subscription.monthly_credits = self._get_tier_credits(new_tier)

            await self.db.commit()
            await self.db.refresh(subscription)

            logger.info(f"Changed subscription {subscription.id} from {old_tier} to {new_tier}")

            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error changing tier: {e}")
            raise RuntimeError(f"Failed to change subscription tier: {str(e)}")

    async def _get_or_create_stripe_customer(self, user: User) -> StripeCustomer:
        """
        Get existing Stripe customer or create new one.

        Args:
            user: User object

        Returns:
            StripeCustomer object
        """
        # Check if customer already exists
        result = await self.db.execute(
            select(StripeCustomer).where(StripeCustomer.user_id == user.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Create new Stripe customer
        try:
            stripe_customer = stripe.Customer.create(
                email=user.email,
                metadata={
                    "user_id": str(user.id),
                    "clerk_user_id": user.clerk_user_id
                }
            )

            # Create local customer record
            customer = StripeCustomer(
                user_id=user.id,
                stripe_customer_id=stripe_customer.id,
                email=user.email,
                name=user.username
            )

            self.db.add(customer)
            await self.db.commit()
            await self.db.refresh(customer)

            logger.info(f"Created Stripe customer {stripe_customer.id} for user {user.id}")

            return customer

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            raise RuntimeError(f"Failed to create Stripe customer: {str(e)}")


    # ============================================================================
    # WEBHOOK HANDLERS - Called directly by FastAPI webhook endpoint
    # ============================================================================

    async def handle_subscription_created(self, stripe_subscription_dict: Dict[str, Any]) -> Subscription:
        """
        Handle customer.subscription.created webhook.
        Creates subscription record and grants initial credits.

        Args:
            stripe_subscription_dict: Stripe subscription object as dict

        Returns:
            Created Subscription object
        """
        # Get user ID from metadata
        user_id_str = stripe_subscription_dict["metadata"].get("user_id")
        if not user_id_str:
            logger.error("user_id not found in subscription metadata")
            raise ValueError("user_id not found in subscription metadata")

        user_id = UUID(user_id_str)

        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()

        # Check if user already has a subscription (duplicate webhook or race condition)
        existing_sub_result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        existing_sub = existing_sub_result.scalar_one_or_none()

        if existing_sub:
            logger.warning(
                f"User {user_id} already has subscription {existing_sub.id}. "
                f"Skipping duplicate subscription.created webhook for {stripe_subscription_dict['id']}"
            )
            # Return existing subscription - this is a duplicate webhook
            return existing_sub

        # Extract subscription details
        price_data = stripe_subscription_dict["items"]["data"][0]["price"]
        tier = stripe_subscription_dict["metadata"].get("tier")
        monthly_credits = self._get_tier_credits(tier)

        # Create subscription record
        # Note: Use billing_cycle_anchor as fallback for current_period_start
        period_start = stripe_subscription_dict.get("current_period_start") or stripe_subscription_dict.get("billing_cycle_anchor") or stripe_subscription_dict.get("start_date")
        period_end = stripe_subscription_dict.get("current_period_end")

        # Calculate period_end if not provided (happens with incomplete subscriptions)
        if not period_end and period_start:
            from dateutil.relativedelta import relativedelta
            start_dt = datetime.fromtimestamp(period_start)
            billing_interval = price_data["recurring"]["interval"]
            if billing_interval == "month":
                end_dt = start_dt + relativedelta(months=1)
            elif billing_interval == "year":
                end_dt = start_dt + relativedelta(years=1)
            else:
                # Default to 30 days if unknown interval
                end_dt = start_dt + relativedelta(days=30)
            period_end = int(end_dt.timestamp())

        try:
            subscription = Subscription(
                user_id=user.id,
                stripe_subscription_id=stripe_subscription_dict["id"],
                stripe_customer_id=stripe_subscription_dict["customer"],
                stripe_price_id=price_data["id"],  # CRITICAL: Track which price
                tier=tier,
                billing_interval=price_data["recurring"]["interval"],
                monthly_credits=monthly_credits,
                status=stripe_subscription_dict["status"],
                current_period_start=datetime.fromtimestamp(period_start) if period_start else datetime.utcnow(),
                current_period_end=datetime.fromtimestamp(period_end) if period_end else datetime.utcnow() + relativedelta(months=1),
                amount_cents=price_data["unit_amount"],
                currency=price_data["currency"].upper(),
                cancel_at_period_end=stripe_subscription_dict.get("cancel_at_period_end", False)
            )

            self.db.add(subscription)
            await self.db.flush()

            # Grant initial monthly credits using CreditService
            from app.services.credit_service import CreditService
            credit_service = CreditService(self.db)

            await credit_service.add_credits_atomic(
                user_id=user.id,
                credits=monthly_credits,
                transaction_type="subscription_grant",
                description=f"Initial credits for {tier} subscription",
                subscription_id=subscription.id,
                stripe_invoice_id=None  # Initial grant doesn't have invoice yet
            )

            await self.db.commit()
            await self.db.refresh(subscription)

            logger.info(f"Subscription created: {subscription.id} for user {user.id}, granted {monthly_credits} credits")

            return subscription

        except IntegrityError as e:
            # Race condition: subscription was created between our check and insert
            await self.db.rollback()
            logger.warning(
                f"IntegrityError creating subscription for user {user_id}. "
                f"Likely duplicate webhook or race condition. Error: {e}"
            )

            # Fetch the existing subscription
            result = await self.db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            existing_sub = result.scalar_one_or_none()

            if existing_sub:
                logger.info(f"Returning existing subscription {existing_sub.id} for user {user_id}")
                return existing_sub
            else:
                # This shouldn't happen, but re-raise if we can't find the subscription
                logger.error(f"IntegrityError occurred but no subscription found for user {user_id}")
                raise

    async def handle_invoice_paid(self, stripe_invoice_dict: Dict[str, Any]) -> None:
        """
        Handle invoice.paid webhook.
        Grants monthly credits on renewal.

        Args:
            stripe_invoice_dict: Stripe invoice object as dict
        """
        # Skip if not a subscription invoice
        if not stripe_invoice_dict.get("subscription"):
            logger.info("Skipping non-subscription invoice")
            return

        # Find subscription
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_invoice_dict["subscription"]
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription not found for invoice {stripe_invoice_dict['id']}")
            return

        # Check if this is a renewal (not initial payment)
        # Initial payment is handled by subscription.created
        # We can check billing_reason field
        billing_reason = stripe_invoice_dict.get("billing_reason")
        is_renewal = billing_reason == "subscription_cycle"

        if is_renewal:
            # Grant monthly credits using CreditService (with idempotency)
            from app.services.credit_service import CreditService
            credit_service = CreditService(self.db)

            result = await credit_service.add_credits_atomic(
                user_id=subscription.user_id,
                credits=subscription.monthly_credits,
                transaction_type="monthly_renewal",
                description=f"Monthly renewal: {subscription.tier} plan",
                subscription_id=subscription.id,
                stripe_invoice_id=stripe_invoice_dict["id"],  # For idempotency
                amount_cents=stripe_invoice_dict.get("amount_paid")
            )

            if result["duplicate"]:
                logger.info(f"Duplicate invoice {stripe_invoice_dict['id']} - credits already granted")
            else:
                logger.info(f"Monthly credits granted: {subscription.monthly_credits} for subscription {subscription.id}")

        # Update period dates from invoice line items (no separate API call needed)
        # Invoice contains the billing period information
        if stripe_invoice_dict.get("lines") and stripe_invoice_dict["lines"].get("data"):
            line_item = stripe_invoice_dict["lines"]["data"][0]
            if line_item.get("period"):
                period = line_item["period"]
                subscription.current_period_start = datetime.fromtimestamp(period["start"])
                subscription.current_period_end = datetime.fromtimestamp(period["end"])
                logger.info(
                    f"Updated subscription {subscription.id} period: "
                    f"{subscription.current_period_start} to {subscription.current_period_end}"
                )

        # Commit all changes together (credits grant + period update)
        await self.db.commit()

    async def handle_subscription_updated(self, stripe_subscription_dict: Dict[str, Any]) -> None:
        """
        Handle customer.subscription.updated webhook.
        Updates subscription status, handles cancellations, tier changes.

        Args:
            stripe_subscription_dict: Stripe subscription object as dict
        """
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_dict["id"]
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription not found: {stripe_subscription_dict['id']}")
            return

        # Update status
        old_status = subscription.status
        subscription.status = stripe_subscription_dict["status"]
        subscription.cancel_at_period_end = stripe_subscription_dict.get("cancel_at_period_end", False)

        # Handle tier change (upgrade/downgrade)
        new_tier = stripe_subscription_dict["metadata"].get("tier")
        if new_tier and new_tier != subscription.tier:
            old_tier = subscription.tier
            subscription.tier = new_tier
            subscription.monthly_credits = self._get_tier_credits(new_tier)

            # Update price ID
            price_data = stripe_subscription_dict["items"]["data"][0]["price"]
            subscription.stripe_price_id = price_data["id"]
            subscription.amount_cents = price_data["unit_amount"]

            logger.info(f"Subscription tier changed: {old_tier} → {new_tier} for subscription {subscription.id}")

        # Update period
        subscription.current_period_start = datetime.fromtimestamp(stripe_subscription_dict["current_period_start"])
        subscription.current_period_end = datetime.fromtimestamp(stripe_subscription_dict["current_period_end"])

        await self.db.commit()

        logger.info(f"Subscription updated: {subscription.id}, status: {old_status} → {subscription.status}")

    async def handle_subscription_deleted(self, stripe_subscription_dict: Dict[str, Any]) -> None:
        """
        Handle customer.subscription.deleted webhook.

        ⚠️ INTENTIONAL BEHAVIOR: Zeros out ALL user credits when subscription ends.

        This applies to:
        - Remaining monthly subscription credits
        - Previously purchased top-up credits

        Rationale: Subscription cancellation results in complete loss of platform access
        and all associated credits. This enforces that credits are subscription-dependent.

        Users should be warned about this behavior before cancelling.

        Args:
            stripe_subscription_dict: Stripe subscription object as dict
        """
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_dict["id"]
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription not found: {stripe_subscription_dict['id']}")
            return

        # Get user with lock
        result = await self.db.execute(
            select(User)
            .where(User.id == subscription.user_id)
            .with_for_update()
        )
        user = result.scalar_one()

        # ⚠️ BUSINESS POLICY: Zero out ALL credits (subscription + top-ups)
        # This is intentional - credits are forfeit on subscription cancellation
        # See docstring above for rationale
        old_balance = user.credits
        user.credits = 0

        # Update subscription
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.utcnow()

        # Create transaction record for audit trail
        from app.services.credit_service import CreditService
        credit_service = CreditService(self.db)

        transaction = CreditTransaction(
            user_id=user.id,
            subscription_id=subscription.id,
            transaction_type="cancellation_reset",
            credits_amount=-old_balance,  # Negative (removed)
            previous_balance=old_balance,
            new_balance=0,
            description=f"Subscription cancelled - all credits reset",
            status='completed',
            completed_at=datetime.utcnow()
        )

        self.db.add(transaction)
        await self.db.commit()

        logger.info(f"Subscription deleted: {subscription.id}, credits reset {old_balance} → 0")

    async def handle_top_up_purchase(self, checkout_session_dict: Dict[str, Any]) -> None:
        """
        Handle checkout.session.completed webhook for top-up purchases.
        Grants top-up credits when payment is successful.

        Args:
            checkout_session_dict: Stripe checkout session object as dict
        """
        # Check if this is a top-up purchase (mode = 'payment', not 'subscription')
        if checkout_session_dict.get('mode') != 'payment':
            logger.info(f"Skipping non-payment checkout session {checkout_session_dict.get('id')}")
            return

        # Get metadata
        metadata = checkout_session_dict.get('metadata', {})
        purchase_type = metadata.get('type')

        if purchase_type != 'top_up':
            logger.info(f"Skipping non-top-up purchase {checkout_session_dict.get('id')}")
            return

        # Extract purchase details from metadata
        user_id_str = metadata.get('user_id')
        package = metadata.get('package')
        credits = int(metadata.get('credits', 0))
        discount_percent = float(metadata.get('discount_percent', 0.0))

        if not user_id_str or not package or credits == 0:
            logger.error(f"Invalid top-up metadata in checkout session {checkout_session_dict.get('id')}")
            return

        user_id = UUID(user_id_str)

        # Get IDs for idempotency (both session and payment intent)
        checkout_session_id = checkout_session_dict.get('id')
        payment_intent_id = checkout_session_dict.get('payment_intent')
        amount_paid = checkout_session_dict.get('amount_total')  # In cents

        # Grant credits using CreditService (with idempotency)
        from app.services.credit_service import CreditService
        credit_service = CreditService(self.db)

        result = await credit_service.add_credits_atomic(
            user_id=user_id,
            credits=credits,
            transaction_type="top_up_purchase",
            description=f"Top-up purchase: {package} package ({credits} credits)",
            stripe_session_id=checkout_session_id,
            stripe_payment_intent_id=payment_intent_id,
            top_up_package=package,
            discount_applied=discount_percent,
            amount_cents=amount_paid
        )

        # Commit the transaction (CRITICAL: without this, credits aren't actually saved!)
        await self.db.commit()

        if result["duplicate"]:
            logger.info(f"Duplicate top-up payment {payment_intent_id} - credits already granted")
        else:
            logger.info(
                f"Top-up purchase completed: {credits} credits granted to user {user_id}, "
                f"package: {package}, discount: {discount_percent * 100}%"
            )
