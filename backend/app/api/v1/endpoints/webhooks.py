"""
Webhook endpoints for Stripe and Instagram.

CRITICAL SECURITY:
- ALL webhooks MUST be signature-verified
- Return 200 quickly (< 30 seconds to prevent timeout)
- Idempotency built into handlers (safe to retry)
"""

from fastapi import APIRouter, Request, HTTPException, Header, Depends, Query
import stripe
import logging
from sqlalchemy.exc import OperationalError, DatabaseError, IntegrityError
from typing import Optional
import inngest

from app.core.config import settings
from app.core.database import get_db
from app.services.subscription_service import SubscriptionService
from app.services.instagram.graph_api import InstagramGraphAPIClient
from app.exceptions import BusinessLogicError, TransientError, ConfigurationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import InstagramEngagement, EngagementType, EngagementStatus

router = APIRouter()
logger = logging.getLogger(__name__)


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
        raise ConfigurationError(
            "STRIPE_WEBHOOK_SECRET not configured - webhook processing cannot continue",
            config_key="STRIPE_WEBHOOK_SECRET"
        )

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
            # Handle both subscription checkouts and top-up purchases
            mode = event_data.get('mode')
            if mode == 'subscription':
                # New subscription purchase - link session to transaction
                await subscription_service.handle_checkout_session_subscription(event_data)
            elif mode == 'payment':
                # Top-up purchase - grant credits
                await subscription_service.handle_top_up_purchase(event_data)
            else:
                logger.warning(f"Unknown checkout mode: {mode}")

        else:
            # Unhandled event type - log and ignore
            logger.info(f"Unhandled webhook event type: {event_type}")

        logger.info(f"Webhook processed successfully: {event_type} (ID: {event.id})")

    except BusinessLogicError as e:
        # ⚠️ BUSINESS LOGIC ERROR: Invalid data, duplicate subscription, etc.
        # Return 200 - these are permanent errors, retry won't help
        logger.warning(
            f"⚠️ BUSINESS LOGIC ERROR in webhook {event_type}: {e.message}",
            extra={
                "event_id": event.id,
                "event_type": event_type,
                "error_details": e.details
            }
        )
        # Return success so Stripe doesn't retry - this is a permanent error

    except TransientError as e:
        # 🚨 TRANSIENT ERROR: Temporary issue that might succeed on retry
        # Return 500 so Stripe retries with exponential backoff
        logger.error(
            f"❌ TRANSIENT ERROR processing webhook {event_type}: {e.message}",
            exc_info=True,
            extra={
                "event_id": event.id,
                "event_type": event_type,
                "error_details": e.details,
                "original_exception": str(e.original_exception) if e.original_exception else None
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Transient error processing webhook. Stripe will retry."
        )

    except ConfigurationError as e:
        # 🔧 CONFIGURATION ERROR: Missing API keys, etc.
        # This should have been caught by startup validation, but handle it gracefully
        logger.error(
            f"❌ CONFIGURATION ERROR processing webhook {event_type}: {e.message}",
            extra={
                "event_id": event.id,
                "event_type": event_type,
                "config_key": e.config_key
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Configuration error: {e.message}"
        )

    except (OperationalError, DatabaseError) as e:
        # 🚨 INFRASTRUCTURE ERROR: Database connection/query failure
        # Wrap as TransientError for consistent handling
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


# ============================================================================
# Instagram Graph API Webhooks
# ============================================================================


@router.get("/instagram")
async def instagram_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Instagram webhook verification endpoint.

    When you configure the webhook in Meta's dashboard, Instagram will send a GET request
    to verify the endpoint. We must respond with the challenge string.

    Query params:
        hub.mode: Should be "subscribe"
        hub.challenge: Random string to echo back
        hub.verify_token: Must match INSTAGRAM_WEBHOOK_VERIFY_TOKEN

    Docs: https://developers.facebook.com/docs/graph-api/webhooks/getting-started#verification-requests
    """
    logger.info(f"Instagram webhook verification request: mode={hub_mode}")

    instagram_client = InstagramGraphAPIClient()

    # Verify the webhook
    challenge = instagram_client.verify_webhook(hub_mode, hub_verify_token, hub_challenge)

    if challenge:
        logger.info("Instagram webhook verification successful")
        return challenge  # Return the challenge string as-is
    else:
        logger.error("Instagram webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/instagram")
async def instagram_webhook_handler(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Instagram webhook event receiver.

    Receives mention notifications when someone tags @sampletheinternet in a post.

    Webhook events we care about:
    - mentions: User tagged our account in a post
    - media: New media was posted (if subscribed)

    Flow:
    1. Receive webhook with media_id
    2. Create InstagramEngagement record (PENDING)
    3. Trigger Inngest job to process video and post comment
    4. Return 200 quickly (Instagram expects < 30s response)

    Docs: https://developers.facebook.com/docs/instagram-api/guides/webhooks
    """
    # Read webhook payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse Instagram webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info(f"Received Instagram webhook: {payload}")

    # Instagram webhook structure:
    # {
    #   "object": "instagram",
    #   "entry": [
    #     {
    #       "id": "instagram_business_account_id",
    #       "time": 1234567890,
    #       "changes": [
    #         {
    #           "field": "mentions",
    #           "value": {
    #             "media_id": "123456789",
    #             "comment_id": "987654321"  # If mentioned in comment
    #           }
    #         }
    #       ]
    #     }
    #   ]
    # }

    # Validate payload structure
    if payload.get("object") != "instagram":
        logger.warning(f"Unexpected webhook object type: {payload.get('object')}")
        return {"status": "ignored"}

    # Process each entry
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})

            if field == "mentions":
                # Someone tagged us in a post!
                media_id = value.get("media_id")

                if not media_id:
                    logger.warning("Mention webhook missing media_id")
                    continue

                try:
                    # Check if we've already processed this mention (idempotency)
                    stmt = select(InstagramEngagement).where(
                        InstagramEngagement.instagram_media_id == media_id
                    )
                    result = await db.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        logger.info(f"Mention already processed: {media_id}")
                        continue

                    # Create engagement record
                    engagement = InstagramEngagement(
                        instagram_media_id=media_id,
                        engagement_type=EngagementType.MENTION,
                        status=EngagementStatus.PENDING,
                        webhook_payload=payload
                    )
                    db.add(engagement)
                    await db.commit()
                    await db.refresh(engagement)

                    logger.info(f"Created Instagram engagement record: {engagement.id}")

                    # Trigger Instagram video processing via mention processor
                    from app.services.instagram.mention_processor import process_instagram_mention
                    try:
                        sample_id = await process_instagram_mention(media_id)
                        if sample_id:
                            logger.info(f"Successfully triggered Instagram processing for sample {sample_id}")
                        else:
                            logger.warning(f"Instagram processing skipped for media_id={media_id}")
                    except Exception as e:
                        logger.error(f"Error triggering Instagram processing: {e}", exc_info=True)

                except Exception as e:
                    logger.error(f"Error processing Instagram mention: {e}", exc_info=True)
                    await db.rollback()
                    # Continue processing other entries - don't fail entire webhook

            elif field == "comments":
                # Someone mentioned us in a comment!
                comment_id = value.get("id")
                media_id = value.get("media_id")
                text = value.get("text", "")

                logger.info(f"Received comment webhook: comment_id={comment_id}, media_id={media_id}, text={text[:100]}")

                # Check if comment mentions our account
                if "@sampletheinternet" not in text.lower():
                    logger.info("Comment doesn't mention our account, ignoring")
                    continue

                if not media_id:
                    logger.warning("Comment webhook missing media_id")
                    continue

                try:
                    # Check if we've already processed this media (idempotency)
                    stmt = select(InstagramEngagement).where(
                        InstagramEngagement.instagram_media_id == media_id
                    )
                    result = await db.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        logger.info(f"Media already processed (via comment mention): {media_id}")
                        continue

                    # Create engagement record
                    engagement = InstagramEngagement(
                        instagram_media_id=media_id,
                        engagement_type=EngagementType.COMMENT,
                        status=EngagementStatus.PENDING,
                        webhook_payload=payload,
                        comment_text=text
                    )
                    db.add(engagement)
                    await db.commit()
                    await db.refresh(engagement)

                    logger.info(f"Created Instagram engagement record from comment: {engagement.id}")

                    # Trigger Instagram video processing via mention processor
                    from app.services.instagram.mention_processor import process_instagram_mention
                    try:
                        sample_id = await process_instagram_mention(media_id)
                        if sample_id:
                            logger.info(f"Successfully triggered Instagram processing for sample {sample_id}")
                        else:
                            logger.warning(f"Instagram processing skipped for media_id={media_id}")
                    except Exception as e:
                        logger.error(f"Error triggering Instagram processing: {e}", exc_info=True)

                except Exception as e:
                    logger.error(f"Error processing Instagram comment mention: {e}", exc_info=True)
                    await db.rollback()
                    # Continue processing other entries - don't fail entire webhook

            else:
                logger.info(f"Unhandled Instagram webhook field: {field}")

    # Always return 200 - Instagram expects quick response
    return {"status": "received"}


@router.get("/instagram/health")
async def instagram_webhook_health():
    """Health check for Instagram webhook endpoint"""
    instagram_client = InstagramGraphAPIClient()
    return {
        "status": "healthy",
        "instagram_configured": instagram_client.is_configured(),
        "has_access_token": bool(settings.INSTAGRAM_ACCESS_TOKEN),
        "has_verify_token": bool(settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN)
    }
