from pydantic import BaseModel, EmailStr, HttpUrl, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum
import re


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    id: UUID
    is_active: bool
    is_superuser: bool
    credits: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: UUID
    credits: int
    created_at: datetime

    class Config:
        from_attributes = True


# Sample Schemas
class SampleBase(BaseModel):
    tiktok_url: HttpUrl
    description: Optional[str] = None


class TikTokURLInput(BaseModel):
    url: HttpUrl

    @validator('url')
    def validate_tiktok_url(cls, v):
        url_str = str(v)
        tiktok_pattern = r'(https?://)?(www\.)?(tiktok\.com|vm\.tiktok\.com)/.*'
        if not re.match(tiktok_pattern, url_str):
            raise ValueError('Invalid TikTok URL format')
        return v


class SampleCreate(BaseModel):
    tiktok_url: HttpUrl


class SampleUpdate(BaseModel):
    description: Optional[str] = None
    genre: Optional[str] = None
    tags: Optional[List[str]] = None


class SampleInDB(BaseModel):
    id: UUID
    tiktok_url: str
    tiktok_id: Optional[str]
    aweme_id: Optional[str]
    title: Optional[str]
    region: Optional[str]
    creator_username: Optional[str]
    creator_name: Optional[str]
    creator_avatar_url: Optional[str]
    creator_avatar_thumb: Optional[str]
    creator_avatar_medium: Optional[str]
    creator_avatar_large: Optional[str]
    creator_signature: Optional[str]
    creator_verified: int
    creator_follower_count: int
    creator_following_count: int
    creator_heart_count: int
    creator_video_count: int
    description: Optional[str]
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    upload_timestamp: Optional[int]
    duration_seconds: Optional[float]
    bpm: Optional[int]
    key: Optional[str]
    genre: Optional[str]
    tags: List[str]
    audio_url_wav: Optional[str]
    audio_url_mp3: Optional[str]
    waveform_url: Optional[str]
    thumbnail_url: Optional[str]
    origin_cover_url: Optional[str]
    music_url: Optional[str]
    video_url: Optional[str]
    video_url_watermark: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TikTokCreatorResponse(BaseModel):
    id: UUID
    tiktok_id: str
    username: str
    nickname: Optional[str] = None
    avatar_thumb: Optional[str] = None
    avatar_medium: Optional[str] = None
    avatar_large: Optional[str] = None
    signature: Optional[str] = None
    verified: bool = False
    follower_count: int = 0
    following_count: int = 0
    heart_count: int = 0
    video_count: int = 0

    class Config:
        from_attributes = True


class SampleResponse(BaseModel):
    id: UUID
    tiktok_url: Optional[str] = None
    tiktok_id: Optional[str] = None
    aweme_id: Optional[str] = None
    title: Optional[str] = None
    region: Optional[str] = None
    creator_username: Optional[str] = None
    creator_name: Optional[str] = None
    creator_avatar_url: Optional[str] = None
    creator_avatar_thumb: Optional[str] = None
    creator_avatar_medium: Optional[str] = None
    creator_avatar_large: Optional[str] = None
    creator_signature: Optional[str] = None
    creator_verified: Optional[bool] = False
    creator_follower_count: Optional[int] = 0
    creator_following_count: Optional[int] = 0
    creator_heart_count: Optional[int] = 0
    creator_video_count: Optional[int] = 0
    description: Optional[str] = None
    view_count: Optional[int] = 0
    like_count: Optional[int] = 0
    share_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    upload_timestamp: Optional[int] = None
    duration_seconds: Optional[float] = None
    bpm: Optional[int] = None
    key: Optional[str] = None
    genre: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)  # Legacy: kept for backward compatibility
    audio_url_wav: Optional[str] = None
    audio_url_mp3: Optional[str] = None
    waveform_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    origin_cover_url: Optional[str] = None
    music_url: Optional[str] = None
    video_url: Optional[str] = None
    video_url_watermark: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    # Nested creator object
    tiktok_creator: Optional[TikTokCreatorResponse] = None

    # Tag objects (forward reference, will be defined below)
    tag_objects: List['TagResponse'] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SampleDownloadResponse(BaseModel):
    download_url: str
    format: str
    expires_at: datetime


# Processing Schemas
class ProcessingTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    sample_id: Optional[UUID] = None


class ProcessingStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    result: Optional[Dict[str, Any]] = None


# Pagination
class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    skip: int
    limit: int
    has_more: bool


class SamplesListResponse(BaseModel):
    items: List[SampleResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


# Tag Schemas
class TagCategoryEnum(str, Enum):
    """Tag categories for frontend"""
    GENRE = "genre"
    MOOD = "mood"
    INSTRUMENT = "instrument"
    CONTENT = "content"
    TEMPO = "tempo"
    EFFECT = "effect"
    OTHER = "other"


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Tag name (will be normalized)")
    category: TagCategoryEnum = TagCategoryEnum.OTHER


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=50)
    category: Optional[TagCategoryEnum] = None


class TagResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    category: TagCategoryEnum
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class TagWithSamplesResponse(TagResponse):
    """Tag response with sample count"""
    sample_count: int = 0


class PopularTagsResponse(BaseModel):
    tags: List[TagResponse]
    total: int


class AddTagsRequest(BaseModel):
    tag_names: List[str] = Field(..., min_items=1, max_items=20, description="List of tag names to add")


class TagSuggestion(BaseModel):
    """Suggested tag with confidence score"""
    name: str
    display_name: str
    category: TagCategoryEnum
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str  # Why this tag is suggested


class TagSuggestionsResponse(BaseModel):
    suggestions: List[TagSuggestion]
    sample_id: UUID