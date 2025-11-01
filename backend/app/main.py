from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import inngest.fast_api
from slowapi.errors import RateLimitExceeded
import sys
import logging

from app.core.config import settings
from app.api.v1.router import api_router
from app.inngest_functions import inngest_client, get_all_functions
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)


def validate_production_config():
    """
    Validate critical configuration for production deployments.

    This function ensures that required secrets and API keys are configured
    before the application starts, preventing runtime failures and security issues.

    FAIL-FAST PRINCIPLE: It's better to fail at startup than to have configuration
    errors discovered during operation (e.g., infinite webhook retries).

    Raises:
        SystemExit: If critical configuration is missing in production
    """
    if settings.ENVIRONMENT.lower() not in ["production", "prod"]:
        logger.info(f"Running in {settings.ENVIRONMENT} environment - skipping production config validation")
        return

    logger.info("Validating production configuration...")

    errors = []

    # Critical: Admin API Key (prevents JWT secret reuse)
    if not settings.ADMIN_API_KEY:
        errors.append(
            "ADMIN_API_KEY is not configured. Admin endpoints require a separate API key "
            "to prevent SECRET_KEY compromise from affecting authentication."
        )

    # Critical: Stripe Webhook Secret (prevents infinite retries)
    if not settings.STRIPE_WEBHOOK_SECRET:
        errors.append(
            "STRIPE_WEBHOOK_SECRET is not configured. Without this, webhook signature "
            "verification will fail and Stripe will retry webhooks infinitely (causing "
            "thousands of failed requests)."
        )

    # Critical: Stripe Secret Key (required for payment processing)
    if not settings.STRIPE_SECRET_KEY:
        errors.append(
            "STRIPE_SECRET_KEY is not configured. This is required for all Stripe "
            "operations including subscriptions and payments."
        )

    # Critical: La La AI API Key (required for stem separation feature)
    if not settings.LALAL_API_KEY:
        errors.append(
            "LALAL_API_KEY is not configured. This is required for stem separation "
            "functionality. If you don't plan to use stem separation, you can ignore this, "
            "but the feature will not work."
        )

    # Warning: Stripe Price IDs (subscriptions won't work without these)
    if not settings.STRIPE_PRICE_BASIC_MONTHLY:
        logger.warning("STRIPE_PRICE_BASIC_MONTHLY not configured - subscription creation will fail")

    if errors:
        logger.error("❌ PRODUCTION CONFIGURATION VALIDATION FAILED:")
        for i, error in enumerate(errors, 1):
            logger.error(f"  {i}. {error}")
        logger.error("\nDeployment halted. Fix configuration and try again.")
        sys.exit(1)

    logger.info("✅ Production configuration validation passed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Validate production configuration (fail-fast)
    validate_production_config()

    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Add rate limiter state
app.state.limiter = limiter


# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    Returns 429 status with retry information.
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc.detail) if hasattr(exc, 'detail') else None
        },
        headers={"Retry-After": "60"}  # Suggest retry after 60 seconds
    )

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip('/') for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Add Inngest serve endpoint
inngest.fast_api.serve(
    app,
    inngest_client,
    get_all_functions(),
    serve_path="/api/inngest"
)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}