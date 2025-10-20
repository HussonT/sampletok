"""
Tag management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.tag import Tag, TagCategory
from app.models.sample import Sample
from app.models.schemas import (
    TagResponse,
    TagCreate,
    TagUpdate,
    PopularTagsResponse,
    AddTagsRequest,
    TagSuggestionsResponse,
    TagCategoryEnum
)
from app.services.tag_service import TagService


router = APIRouter()


@router.get("/", response_model=List[TagResponse])
async def list_tags(
    category: Optional[TagCategoryEnum] = None,
    search: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all tags with optional filtering
    """
    if search:
        # Search tags
        tags = await TagService.search_tags(db, search, limit)
        return tags

    query = select(Tag)

    if category:
        # Convert string enum to TagCategory
        tag_category = TagCategory[category.value.upper()]
        query = query.where(Tag.category == tag_category)

    query = query.order_by(Tag.usage_count.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    tags = list(result.scalars().all())

    return tags


@router.get("/popular", response_model=PopularTagsResponse)
async def get_popular_tags(
    limit: int = Query(default=30, ge=1, le=100),
    category: Optional[TagCategoryEnum] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get popular tags ordered by usage count
    """
    tag_category = None
    if category:
        tag_category = TagCategory[category.value.upper()]

    tags = await TagService.get_popular_tags(db, limit, tag_category)

    return PopularTagsResponse(
        tags=tags,
        total=len(tags)
    )


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific tag by ID
    """
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id)
    )
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    return tag


@router.post("/", response_model=TagResponse)
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new tag (admin endpoint)
    """
    # Convert enum to TagCategory
    tag_category = TagCategory[tag_data.category.value.upper()]

    # Check if tag already exists
    normalized_name = TagService.normalize_tag_name(tag_data.name)
    result = await db.execute(
        select(Tag).where(Tag.name == normalized_name)
    )
    existing_tag = result.scalar_one_or_none()

    if existing_tag:
        raise HTTPException(
            status_code=400,
            detail=f"Tag '{tag_data.name}' already exists"
        )

    # Create tag
    tag = Tag(
        name=normalized_name,
        display_name=tag_data.name.strip(),
        category=tag_category
    )

    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return tag


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: UUID,
    tag_update: TagUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a tag (admin endpoint)
    """
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id)
    )
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Update fields
    if tag_update.display_name is not None:
        tag.display_name = tag_update.display_name

    if tag_update.category is not None:
        tag.category = TagCategory[tag_update.category.value.upper()]

    await db.commit()
    await db.refresh(tag)

    return tag


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a tag (admin endpoint)
    """
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id)
    )
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    await db.delete(tag)
    await db.commit()

    return {"message": "Tag deleted successfully"}


@router.post("/samples/{sample_id}/tags", response_model=List[TagResponse])
async def add_tags_to_sample(
    sample_id: UUID,
    tags_request: AddTagsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Add tags to a sample
    """
    # Get sample with tags loaded
    result = await db.execute(
        select(Sample)
        .options(selectinload(Sample.tag_objects))
        .where(Sample.id == sample_id)
    )
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    # Add tags
    added_tags = await TagService.add_tags_to_sample(
        db,
        sample,
        tags_request.tag_names,
        auto_categorize=True
    )

    await db.commit()

    # Return all tags for this sample
    await db.refresh(sample)
    result = await db.execute(
        select(Sample)
        .options(selectinload(Sample.tag_objects))
        .where(Sample.id == sample_id)
    )
    sample = result.scalar_one_or_none()

    return sample.tag_objects


@router.delete("/samples/{sample_id}/tags/{tag_name}")
async def remove_tag_from_sample(
    sample_id: UUID,
    tag_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a tag from a sample
    """
    # Get sample with tags loaded
    result = await db.execute(
        select(Sample)
        .options(selectinload(Sample.tag_objects))
        .where(Sample.id == sample_id)
    )
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    # Remove tag
    removed = await TagService.remove_tag_from_sample(db, sample, tag_name)

    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Tag '{tag_name}' not found on this sample"
        )

    await db.commit()

    return {"message": f"Tag '{tag_name}' removed successfully"}


@router.get("/samples/{sample_id}/tags", response_model=List[TagResponse])
async def get_sample_tags(
    sample_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all tags for a specific sample
    """
    result = await db.execute(
        select(Sample)
        .options(selectinload(Sample.tag_objects))
        .where(Sample.id == sample_id)
    )
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    return sample.tag_objects


@router.get("/samples/{sample_id}/suggestions", response_model=TagSuggestionsResponse)
async def get_tag_suggestions(
    sample_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get suggested tags for a sample based on its metadata and audio analysis
    """
    result = await db.execute(
        select(Sample).where(Sample.id == sample_id)
    )
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    suggestions = await TagService.generate_suggestions(db, sample)

    return TagSuggestionsResponse(
        suggestions=suggestions,
        sample_id=sample_id
    )
