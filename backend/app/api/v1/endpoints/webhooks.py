"""
Stripe webhook endpoint with signature verification.

This endpoint receives webhooks from Stripe and processes them directly (async).
No Inngest needed - FastAPI's async handlers + Stripe's retry logic is sufficient.

CRITICAL SECURITY:
- ALL webhooks MUST be signature-verified
- Return 200 quickly (< 30 seconds to prevent Stripe timeout)
- Idempotency built into handlers (safe to retry)
"""

from fastapi import APIRouter, Request, HTTPException, Header, Depends
import stripe
import logging
from sqlalchemy.exc import OperationalError, DatabaseError, IntegrityError

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.subscription_service import SubscriptionService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_db():
    """Dependency for database session"""
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/stripe")
async def stripe_webhook_handler(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    🔒 CRITICAL SECURITY: Stripe webhook receiver with signature verification.

    This endpoint:
    1. Verifies webhook signature (prevents attacks)
    2. Processes events asynchronously (FastAPI async)
    3. Returns 200 quickly (< 30 seconds)
    4. Idempotent handlers (safe to retry)

    Supported events:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.paid
    - invoice.payment_failed
    - checkout.session.completed (top-up purchases)

    Returns:
        {"received": True, "event_id": str, "event_type": str}
    """
    # 1️⃣ READ RAW BODY (required for signature verification)
    payload = await request.body()

    # 2️⃣ VERIFY SIGNATURE (CRITICAL SECURITY!)
    if not stripe_signature:
        logger.error("❌ Missing Stripe signature header")
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("❌ STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        # Construct and verify event
        # This ensures the webhook came from Stripe and hasn't been tampered with
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload format
        logger.error(f"❌ Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature - POSSIBLE ATTACK!
        logger.error(f"🚨 SECURITY ALERT: Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 3️⃣ PROCESS EVENT DIRECTLY (async, fast operations)
    event_type = event.type
    event_data = event.data.object

    logger.info(f"Processing webhook: {event_type} (ID: {event.id})")

    try:
        subscription_service = SubscriptionService(db)

        # Route to appropriate handler
        if event_type == "customer.subscription.created":
            await subscription_service.handle_subscription_created(event_data)

        elif event_type == "customer.subscription.updated":
            await subscription_service.handle_subscription_updated(event_data)

        elif event_type == "customer.subscription.deleted":
            await subscription_service.handle_subscription_deleted(event_data)

        elif event_type == "invoice.paid":
            await subscription_service.handle_invoice_paid(event_data)

        elif event_type == "invoice.payment_failed":
            # Log failed payment (subscription goes to past_due)
            logger.warning(f"Payment failed for invoice {event_data.get('id')}")
            # Stripe automatically retries - no action needed

        elif event_type == "checkout.session.completed":
            # Handle top-up purchases (one-time payments)
            await subscription_service.handle_top_up_purchase(event_data)

        else:
            # Unhandled event type - log and ignore
            logger.info(f"Unhandled webhook event type: {event_type}")

        logger.info(f"Webhook processed successfully: {event_type} (ID: {event.id})")

    except (OperationalError, DatabaseError) as e:
        # 🚨 INFRASTRUCTURE ERROR: Database connection/query failure
        # Return 500 so Stripe retries (these are transient errors)
        logger.error(
            f"❌ DATABASE ERROR processing webhook {event_type}: {e}",
            exc_info=True,
            extra={"event_id": event.id, "event_type": event_type}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Database error processing webhook. Stripe will retry."
        )

    except ValueError as e:
        # ⚠️ BUSINESS LOGIC ERROR: Invalid data, duplicate subscription, etc.
        # Return 200 - these are not transient and retry won't help
        logger.warning(
            f"⚠️ BUSINESS LOGIC ERROR in webhook {event_type}: {e}",
            extra={"event_id": event.id, "event_type": event_type}
        )
        # Return success so Stripe doesn't retry

    except stripe.error.StripeError as e:
        # 🚨 STRIPE API ERROR: Failed to fetch subscription details, etc.
        # Return 500 so Stripe retries (Stripe API might be temporarily down)
        logger.error(
            f"❌ STRIPE API ERROR processing webhook {event_type}: {e}",
            exc_info=True,
            extra={"event_id": event.id, "event_type": event_type}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Stripe API error. Stripe will retry."
        )

    except Exception as e:
        # ❓ UNKNOWN ERROR: Could be infrastructure or code bug
        # Log with full context and return 500 to be safe
        logger.error(
            f"❌ UNEXPECTED ERROR processing webhook {event_type}: {e}",
            exc_info=True,
            extra={"event_id": event.id, "event_type": event_type}
        )
        # Return 500 for unknown errors - better to retry than silently fail
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error processing webhook. Stripe will retry."
        )

    # 4️⃣ RETURN SUCCESS
    # Only reached if no exceptions were raised
    return {"received": True, "event_id": event.id, "event_type": event_type}


@router.get("/stripe/health")
async def webhook_health_check():
    """Health check for webhook endpoint"""
    has_secret = bool(settings.STRIPE_WEBHOOK_SECRET)
    return {
        "status": "healthy",
        "webhook_secret_configured": has_secret
    }
