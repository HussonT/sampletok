"""
Credit management endpoints.

Provides endpoints for:
- Viewing credit balance
- Viewing transaction history
- Purchasing top-up credits
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import stripe

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.api.deps import get_current_user
from app.services.credit_service import CreditService
from app.services.subscription_service import SubscriptionService
from app.models.credit_transaction import CreditTransaction
from app.models.schemas import (
    CreditBalanceResponse,
    CreditTransactionResponse,
    CreditTransactionListResponse,
    TopUpRequest,
    TopUpResponse
)

router = APIRouter()


# Top-up package configuration loaded from settings
def get_topup_packages():
    """Get top-up package configuration from settings."""
    return {
        "small": {
            "credits": settings.TOPUP_CREDITS_SMALL,
            "price_cents": settings.TOPUP_PRICE_SMALL_CENTS,
        },
        "medium": {
            "credits": settings.TOPUP_CREDITS_MEDIUM,
            "price_cents": settings.TOPUP_PRICE_MEDIUM_CENTS,
        },
        "large": {
            "credits": settings.TOPUP_CREDITS_LARGE,
            "price_cents": settings.TOPUP_PRICE_LARGE_CENTS,
        }
    }


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's current credit balance and subscription info.

    Returns:
        Credit balance, subscription status, and next renewal date
    """
    # Load subscription relationship
    await db.refresh(current_user, ["subscription"])

    subscription = current_user.subscription
    has_subscription = subscription is not None and subscription.is_active

    return CreditBalanceResponse(
        credits=current_user.credits,
        has_subscription=has_subscription,
        subscription_tier=subscription.tier if has_subscription else None,
        monthly_credits=subscription.monthly_credits if has_subscription else None,
        next_renewal=subscription.current_period_end if has_subscription else None
    )


@router.get("/transactions", response_model=CreditTransactionListResponse)
async def get_credit_transactions(
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return"),
    offset: int = Query(0, ge=0, description="Number of transactions to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's credit transaction history.

    Returns paginated list of all credit movements (grants, deductions, refunds).
    Sorted by most recent first.

    Args:
        limit: Number of transactions to return (1-100)
        offset: Number of transactions to skip (for pagination)

    Returns:
        Paginated list of transactions
    """
    # Get total count
    count_result = await db.execute(
        select(func.count(CreditTransaction.id))
        .where(CreditTransaction.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    # Get transactions
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == current_user.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    transactions = result.scalars().all()

    # Convert to response models
    transaction_responses = [
        CreditTransactionResponse.model_validate(tx)
        for tx in transactions
    ]

    return CreditTransactionListResponse(
        items=transaction_responses,
        total=total,
        skip=offset,
        limit=limit,
        has_more=(offset + len(transactions)) < total
    )


@router.get("/transaction/session/{session_id}", response_model=CreditTransactionResponse)
async def get_transaction_by_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get transaction details by Stripe checkout session ID.

    This is useful for the success page to show how many credits were just added.

    Args:
        session_id: Stripe checkout session ID

    Returns:
        Transaction details including previous_balance, new_balance, and credits_amount

    Raises:
        404: Transaction not found for this session
    """
    result = await db.execute(
        select(CreditTransaction)
        .where(
            CreditTransaction.user_id == current_user.id,
            CreditTransaction.stripe_session_id == session_id
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found for this session"
        )

    return CreditTransactionResponse.model_validate(transaction)


@router.post("/top-up", response_model=TopUpResponse)
async def purchase_top_up(
    request: TopUpRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Purchase top-up credits via Stripe.

    Creates a Stripe checkout session for one-time credit purchase.
    Top-ups require an active subscription and offer tier-based discounts:
    - Basic: No discount
    - Pro: 10% discount
    - Ultimate: 20% discount

    Args:
        package: Package size (small, medium, or large)

    Returns:
        Stripe checkout session URL

    Raises:
        400: No active subscription (required for top-ups)
        404: Invalid package or Stripe not configured
        500: Stripe API error
    """
    # Check subscription requirement
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_user_subscription(current_user.id)

    if not subscription or not subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active subscription required to purchase top-up credits. Please subscribe first."
        )

    # Get package details from config
    topup_packages = get_topup_packages()
    package_details = topup_packages.get(request.package)
    if not package_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid package: {request.package}"
        )

    # Get tier discount from config
    discount_percent = subscription_service._get_tier_discount(subscription.tier)

    # Get or create Stripe customer
    stripe_customer = await subscription_service._get_or_create_stripe_customer(current_user)

    # Create checkout session for one-time purchase
    try:
        # Calculate discounted price
        base_price_cents = package_details["price_cents"]
        discounted_price_cents = int(base_price_cents * (1 - discount_percent))

        # Build line item with dynamic pricing
        # Using price_data allows us to set the exact discounted price
        line_items = [{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"{request.package.capitalize()} Credit Pack",
                    "description": f"{package_details['credits']} credits{f' ({int(discount_percent * 100)}% {subscription.tier} discount applied)' if discount_percent > 0 else ''}",
                },
                "unit_amount": discounted_price_cents,
            },
            "quantity": 1,
        }]

        checkout_params = {
            "customer": stripe_customer.stripe_customer_id,
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": "payment",  # One-time payment
            "success_url": f"{settings.SUBSCRIPTION_SUCCESS_URL}?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": settings.SUBSCRIPTION_CANCEL_URL,
            "metadata": {
                "user_id": str(current_user.id),
                "type": "top_up",
                "package": request.package,
                "credits": package_details["credits"],
                "discount_percent": discount_percent,
                "base_price_cents": base_price_cents,
                "discounted_price_cents": discounted_price_cents
            }
        }

        session = stripe.checkout.Session.create(**checkout_params)

        return TopUpResponse(
            session_id=session.id,
            checkout_url=session.url,
            package=request.package,
            credits=package_details["credits"],
            price_cents=package_details["price_cents"],
            discount_percent=discount_percent
        )

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )
