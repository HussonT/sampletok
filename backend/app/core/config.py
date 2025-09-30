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

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # TikTok Processing
    MAX_VIDEO_DURATION_SECONDS: int = 300
    MAX_CONCURRENT_DOWNLOADS: int = 5
    DOWNLOAD_TIMEOUT_SECONDS: int = 60

    # Audio Processing
    AUDIO_SAMPLE_RATE: int = 48000
    AUDIO_BIT_DEPTH: int = 24
    MP3_BITRATE: int = 320
    WAVEFORM_WIDTH: int = 800
    WAVEFORM_HEIGHT: int = 140

    # RapidAPI Settings
    RAPIDAPI_KEY: str = "36d89111a2msh4ba98e6cc64bc41p1b0c41jsn27ddea8cadd7"
    RAPIDAPI_HOST: str = "tiktok-video-no-watermark2.p.rapidapi.com"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()