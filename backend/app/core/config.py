from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SampleTok"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SECRET_KEY: str
    ENVIRONMENT: str = "development"

    # API
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
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

    # Audio Processing
    AUDIO_SAMPLE_RATE: int = 48000
    AUDIO_BIT_DEPTH: int = 24
    MP3_BITRATE: int = 320
    WAVEFORM_WIDTH: int = 800
    WAVEFORM_HEIGHT: int = 320

    # RapidAPI Settings (must be set in .env)
    RAPIDAPI_KEY: str  # Required - no default for security
    RAPIDAPI_HOST: str = "tiktok-video-no-watermark2.p.rapidapi.com"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()