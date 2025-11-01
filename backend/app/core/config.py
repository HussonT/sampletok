from typing import List, Optional
import json
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SampleTok"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SECRET_KEY: str
    ADMIN_API_KEY: Optional[str] = None  # Separate key for admin endpoints (required in production)
    ENVIRONMENT: str = "development"

    # API
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            # Try to parse as JSON first (for Secret Manager format)
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Otherwise split by comma
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: str
    DATABASE_ECHO: bool = False

    # Inngest
    INNGEST_EVENT_KEY: Optional[str] = None  # Optional - only needed for production
    INNGEST_SIGNING_KEY: Optional[str] = None  # Optional - for webhook verification
    INNGEST_ENV: Optional[str] = None  # Branch environment name (required when using branch keys)

    # Storage
    STORAGE_TYPE: str = "s3"  # "s3" or "r2"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "sampletok-samples"
    S3_ENDPOINT_URL: Optional[str] = None

    # R2-specific (Cloudflare)
    R2_PUBLIC_DOMAIN: Optional[str] = None  # Custom domain for R2 public access
    CLOUDFLARE_TOKEN: Optional[str] = None

    # Clerk Authentication
    CLERK_FRONTEND_API: str  # e.g., "your-app.clerk.accounts.dev"
    CLERK_SECRET_KEY: str  # Backend secret key for API calls

    # TikTok Processing
    MAX_VIDEO_DURATION_SECONDS: int = 300
    MAX_CONCURRENT_DOWNLOADS: int = 5
    DOWNLOAD_TIMEOUT_SECONDS: int = 60

    # TikTok Collections
    MAX_VIDEOS_PER_BATCH: int = 30  # Maximum videos to process in one batch
    MAX_COLLECTIONS_PER_REQUEST: int = 35  # Maximum collections to fetch in one request
    TIKTOK_API_MAX_PER_REQUEST: int = 30  # TikTok API limit per request
    TIKTOK_API_RETRY_ATTEMPTS: int = 3  # Number of retry attempts for inconsistent TikTok API responses
    TIKTOK_API_TIMEOUT_SECONDS: int = 30  # HTTP timeout for TikTok API requests
    CREATOR_CACHE_TTL_HOURS: int = 24  # How long to cache TikTok creator info

    # Rate Limiting
    COLLECTION_RATE_LIMIT_PER_MINUTE: int = 10  # Max collection processing requests per minute per user
    COLLECTIONS_LIST_RATE_LIMIT_PER_MINUTE: int = 60  # Max collection list requests per minute per user
    STEM_SEPARATION_RATE_LIMIT_PER_MINUTE: int = 5  # Max stem separation requests per minute per user
    STEM_DOWNLOAD_RATE_LIMIT_PER_MINUTE: int = 30  # Max stem download requests per minute per user

    # Audio Processing
    AUDIO_SAMPLE_RATE: int = 48000
    AUDIO_BIT_DEPTH: int = 24
    MP3_BITRATE: int = 320
    WAVEFORM_WIDTH: int = 800
    WAVEFORM_HEIGHT: int = 320

    # RapidAPI Settings (must be set in .env)
    RAPIDAPI_KEY: str  # Required - no default for security
    RAPIDAPI_HOST: str = "tiktok-video-no-watermark2.p.rapidapi.com"

    # La La AI Settings
    LALAL_API_KEY: Optional[str] = None  # Required for stem separation
    MAX_STEMS_PER_REQUEST: int = 5  # Maximum number of stems that can be requested at once
    MAX_CONCURRENT_DOWNLOADS_PER_USER: int = 3  # Maximum concurrent stem downloads per user

    # Stripe Settings
    STRIPE_SECRET_KEY: Optional[str] = None  # Required for production
    STRIPE_WEBHOOK_SECRET: Optional[str] = None  # Required for webhook verification
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None  # For frontend
    STRIPE_PORTAL_CONFIGURATION_ID: Optional[str] = None  # Customer Portal configuration

    # Stripe Price IDs - Subscription Plans
    STRIPE_PRICE_BASIC_MONTHLY: Optional[str] = None
    STRIPE_PRICE_BASIC_ANNUAL: Optional[str] = None
    STRIPE_PRICE_PRO_MONTHLY: Optional[str] = None
    STRIPE_PRICE_PRO_ANNUAL: Optional[str] = None
    STRIPE_PRICE_ULTIMATE_MONTHLY: Optional[str] = None
    STRIPE_PRICE_ULTIMATE_ANNUAL: Optional[str] = None

    # Stripe Price IDs - Top-Up Packs
    STRIPE_PRICE_TOPUP_SMALL: Optional[str] = None  # 50 credits
    STRIPE_PRICE_TOPUP_MEDIUM: Optional[str] = None  # 150 credits
    STRIPE_PRICE_TOPUP_LARGE: Optional[str] = None  # 500 credits

    # Subscription Tier Configuration
    TIER_CREDITS_BASIC: int = 100  # Monthly credits for Basic tier
    TIER_CREDITS_PRO: int = 400  # Monthly credits for Pro tier
    TIER_CREDITS_ULTIMATE: int = 1500  # Monthly credits for Ultimate tier

    # Feature Credit Costs
    CREDITS_PER_STEM: int = 2  # Cost per stem separation

    # Top-Up Discounts by Tier (percentage as decimal, e.g., 0.10 = 10% off)
    TIER_DISCOUNT_BASIC: float = 0.0  # No discount for Basic
    TIER_DISCOUNT_PRO: float = 0.10  # 10% discount for Pro
    TIER_DISCOUNT_ULTIMATE: float = 0.20  # 20% discount for Ultimate

    # Top-Up Package Configuration
    TOPUP_CREDITS_SMALL: int = 50  # Small package credits
    TOPUP_PRICE_SMALL_CENTS: int = 699  # Small package price ($6.99)
    TOPUP_CREDITS_MEDIUM: int = 150  # Medium package credits
    TOPUP_PRICE_MEDIUM_CENTS: int = 1799  # Medium package price ($17.99)
    TOPUP_CREDITS_LARGE: int = 500  # Large package credits
    TOPUP_PRICE_LARGE_CENTS: int = 4999  # Large package price ($49.99)

    # Subscription URLs
    SUBSCRIPTION_SUCCESS_URL: str = "http://localhost:3000/subscription/success"
    SUBSCRIPTION_CANCEL_URL: str = "http://localhost:3000/pricing"
    FRONTEND_URL: Optional[str] = "http://localhost:3000"  # For Stripe Customer Portal return URL

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()