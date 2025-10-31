"""
Subscription management endpoints.

Provides endpoints for:
- Creating Stripe checkout sessions
- Viewing current subscription
- Canceling subscriptions
- Upgrading/downgrading tiers
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.api.deps import get_current_user
from app.services.subscription_service import SubscriptionService
from app.models.schemas import (
    CreateCheckoutRequest,
    CheckoutSessionResponse,
    SubscriptionResponse,
    CancelSubscriptionRequest,
    UpgradeSubscriptionRequest
)

router = APIRouter()


# Tier to Stripe Price ID mapping
TIER_PRICE_IDS = {
    ("basic", "month"): settings.STRIPE_PRICE_BASIC_MONTHLY,
    ("basic", "year"): settings.STRIPE_PRICE_BASIC_ANNUAL,
    ("pro", "month"): settings.STRIPE_PRICE_PRO_MONTHLY,
    ("pro", "year"): settings.STRIPE_PRICE_PRO_ANNUAL,
    ("ultimate", "month"): settings.STRIPE_PRICE_ULTIMATE_MONTHLY,
    ("ultimate", "year"): settings.STRIPE_PRICE_ULTIMATE_ANNUAL,
}


@router.post("/create-checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe checkout session for new subscription.

    Returns a checkout URL that redirects user to Stripe's hosted checkout page.
    After successful payment, Stripe webhook will handle subscription creation.

    Raises:
        400: User already has active subscription
        404: Invalid tier/interval combination
        500: Stripe API error
    """
    # Get price ID for tier + interval
    price_id = TIER_PRICE_IDS.get((request.tier, request.billing_interval))

    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price configured for tier '{request.tier}' with interval '{request.billing_interval}'"
        )

    # Create checkout session via service
    subscription_service = SubscriptionService(db)

    try:
        result = await subscription_service.create_checkout_session(
            user=current_user,
            price_id=price_id,
            tier=request.tier,
            billing_interval=request.billing_interval
        )

        return CheckoutSessionResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's current subscription.

    Returns:
        Subscription details including tier, credits, billing info

    Raises:
        404: User has no subscription
    """
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_user_subscription(current_user.id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found. Please subscribe to access the platform."
        )

    return SubscriptionResponse.model_validate(subscription)


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel the authenticated user's subscription.

    Args:
        cancel_at_period_end: If true (default), subscription remains active until period end.
                             If false, cancels immediately and zeros credits.

    Returns:
        Updated subscription details

    Raises:
        404: No active subscription found
        500: Stripe API error
    """
    subscription_service = SubscriptionService(db)

    try:
        subscription = await subscription_service.cancel_subscription(
            user_id=current_user.id,
            cancel_at_period_end=request.cancel_at_period_end
        )

        return SubscriptionResponse.model_validate(subscription)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/upgrade", response_model=SubscriptionResponse)
async def upgrade_subscription(
    request: UpgradeSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upgrade or downgrade subscription tier.

    Changes are prorated - user is charged/credited for the difference.
    Monthly credits are updated to match new tier.

    Args:
        new_tier: Target tier (basic, pro, or ultimate)

    Returns:
        Updated subscription details

    Raises:
        400: Already on this tier or no active subscription
        500: Stripe API error
    """
    subscription_service = SubscriptionService(db)

    # Get current subscription to determine billing interval
    subscription = await subscription_service.get_user_subscription(current_user.id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found. Please subscribe first."
        )

    # Get price ID for new tier with same billing interval
    new_price_id = TIER_PRICE_IDS.get((request.new_tier, subscription.billing_interval))

    if not new_price_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price configured for tier '{request.new_tier}' with interval '{subscription.billing_interval}'"
        )

    try:
        updated_subscription = await subscription_service.change_tier(
            user_id=current_user.id,
            new_price_id=new_price_id,
            new_tier=request.new_tier
        )

        return SubscriptionResponse.model_validate(updated_subscription)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/portal")
async def create_customer_portal_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe Customer Portal session for subscription management.

    Redirects user to Stripe's hosted portal where they can:
    - View subscription details
    - Change payment method
    - View billing history and invoices
    - Cancel subscription
    - Update billing details

    Returns:
        {"portal_url": str} - URL to redirect user to Stripe Customer Portal

    Raises:
        404: User has no subscription
        500: Stripe API error
    """
    subscription_service = SubscriptionService(db)

    # Get user's subscription
    subscription = await subscription_service.get_user_subscription(current_user.id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found. Please subscribe first."
        )

    try:
        # Get or create Stripe customer
        stripe_customer = await subscription_service._get_or_create_stripe_customer(current_user)

        # Create Customer Portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL or 'http://localhost:3000'}/account",
        )

        return {"portal_url": portal_session.url}

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create portal session: {str(e)}"
        )
