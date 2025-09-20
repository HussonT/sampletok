from pydantic import BaseModel, EmailStr, HttpUrl, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
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
    creator_username: Optional[str]
    creator_name: Optional[str]
    description: Optional[str]
    view_count: int
    like_count: int
    duration_seconds: Optional[float]
    bpm: Optional[int]
    key: Optional[str]
    genre: Optional[str]
    tags: List[str]
    audio_url_wav: Optional[str]
    audio_url_mp3: Optional[str]
    waveform_url: Optional[str]
    thumbnail_url: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SampleResponse(BaseModel):
    id: UUID
    creator_username: Optional[str]
    creator_name: Optional[str]
    description: Optional[str]
    view_count: int
    duration_seconds: Optional[float]
    bpm: Optional[int]
    key: Optional[str]
    genre: Optional[str]
    tags: List[str]
    audio_url_mp3: Optional[str]
    waveform_url: Optional[str]
    thumbnail_url: Optional[str]
    status: str
    created_at: datetime

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