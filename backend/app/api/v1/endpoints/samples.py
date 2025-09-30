from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models import Sample, ProcessingStatus
from app.models.schemas import (
    SampleResponse,
    SampleUpdate,
    PaginatedResponse,
    PaginationParams
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_samples(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    genre: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all samples with optional filtering"""
    query = select(Sample)

    # Filter out samples without essential data - only show completed, playable samples
    query = query.where(
        # Must have essential metadata
        Sample.creator_username.isnot(None),
        Sample.creator_username != '',
        Sample.title.isnot(None),
        Sample.title != '',
        # Must have playable audio file
        Sample.audio_url_mp3.isnot(None),
        Sample.audio_url_mp3 != '',
        # Must have waveform for UI display
        Sample.waveform_url.isnot(None),
        Sample.waveform_url != ''
    )

    # Apply status filter - default to COMPLETED only
    if status:
        try:
            status_enum = ProcessingStatus[status.upper()]
            query = query.where(Sample.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    else:
        # By default, only show completed samples
        query = query.where(Sample.status == ProcessingStatus.COMPLETED)

    if genre:
        query = query.where(Sample.genre == genre)

    if search:
        query = query.where(
            Sample.description.ilike(f"%{search}%") |
            Sample.creator_username.ilike(f"%{search}%")
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Sample.created_at.desc())

    # Execute query
    result = await db.execute(query)
    samples = result.scalars().all()

    # Convert to response models
    items = [SampleResponse.model_validate(sample) for sample in samples]

    return PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total
    )


@router.get("/{sample_id}", response_model=SampleResponse)
async def get_sample(
    sample_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific sample by ID"""
    query = select(Sample).where(Sample.id == sample_id)
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    return SampleResponse.model_validate(sample)


@router.patch("/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_id: UUID,
    sample_update: SampleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a sample's metadata"""
    query = select(Sample).where(Sample.id == sample_id)
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    # Update fields
    update_data = sample_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sample, field, value)

    await db.commit()
    await db.refresh(sample)

    return SampleResponse.model_validate(sample)


@router.delete("/{sample_id}")
async def delete_sample(
    sample_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a sample"""
    query = select(Sample).where(Sample.id == sample_id)
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    await db.delete(sample)
    await db.commit()

    return {"message": "Sample deleted successfully"}