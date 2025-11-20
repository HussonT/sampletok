"""
Instagram Mention Processor

Handles the processing of Instagram mentions when users tag @sampletheinternet
in their posts. This includes:
- Fetching media details from Instagram Graph API
- Validating the media is a video
- Checking for duplicates
- Creating sample records
- Triggering the Inngest processing pipeline
- Creating engagement tracking records
"""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import inngest

from app.core.database import AsyncSessionLocal
from app.models import Sample, ProcessingStatus, InstagramEngagement
from app.models.sample import SampleSource
from app.services.instagram.graph_api_service import InstagramGraphAPIService
from app.inngest_functions import inngest_client

logger = logging.getLogger(__name__)


async def process_instagram_mention(media_id: str) -> Optional[str]:
    """
    Process an Instagram mention by creating a sample and triggering the processing pipeline.

    Args:
        media_id: Instagram media ID from the mention event

    Returns:
        Sample ID if successfully queued, None if skipped or failed

    Flow:
        1. Fetch media details from Instagram Graph API
        2. Validate it's a video (skip images/carousels)
        3. Extract shortcode from permalink
        4. Check for duplicates (both sample and engagement)
        5. Create sample record
        6. Create engagement tracking record
        7. Trigger Inngest processing pipeline
    """
    logger.info(f"Starting mention processing for media_id={media_id}")

    # Get database session
    async with AsyncSessionLocal() as db:
        try:
            # Step 1: Check if we've already processed this media
            existing_engagement_query = select(InstagramEngagement).where(
                InstagramEngagement.instagram_media_id == media_id
            )
            result = await db.execute(existing_engagement_query)
            existing_engagement = result.scalars().first()

            if existing_engagement:
                logger.info(
                    f"Duplicate mention detected for media_id={media_id}. "
                    f"Already tracked in engagement {existing_engagement.id}"
                )
                return None

            # Step 2: Fetch media details from Instagram Graph API
            graph_api = InstagramGraphAPIService()

            if not graph_api.is_configured():
                logger.error("Instagram Graph API is not configured. Cannot process mention.")
                return None

            # Get media details including permalink
            media = await graph_api.get_media_details(
                media_id,
                fields=['id', 'media_type', 'media_url', 'permalink', 'caption', 'timestamp', 'username']
            )

            # Step 3: Validate media type (must be VIDEO or CAROUSEL_ALBUM with video)
            # Instagram media types: IMAGE = 1, VIDEO = 2, CAROUSEL_ALBUM = 8
            media_type = media.get('media_type')

            if media_type != 'VIDEO':
                logger.info(
                    f"Skipping non-video media_id={media_id} (type={media_type}). "
                    "Only videos are supported."
                )
                # Still track this so we don't process it again
                await _create_skipped_engagement(db, media_id, media, "Non-video content")
                await db.commit()
                return None

            # Step 4: Extract shortcode from permalink
            permalink = media.get('permalink', '')
            shortcode = InstagramGraphAPIService.extract_shortcode_from_permalink(permalink)

            if not shortcode:
                logger.error(f"Could not extract shortcode from permalink: {permalink}")
                await _create_failed_engagement(db, media_id, media, "Failed to extract shortcode")
                await db.commit()
                return None

            # Step 5: Check if this shortcode was already processed
            existing_sample_query = select(Sample).where(
                Sample.instagram_shortcode == shortcode
            ).order_by(Sample.created_at.desc())
            result = await db.execute(existing_sample_query)
            existing_sample = result.scalars().first()

            if existing_sample:
                logger.info(
                    f"Sample already exists for shortcode={shortcode} (sample_id={existing_sample.id}). "
                    "Linking to existing sample."
                )

                # Create engagement record pointing to existing sample
                engagement = InstagramEngagement(
                    sample_id=existing_sample.id,
                    instagram_media_id=media_id,
                    instagram_post_url=permalink,
                    instagram_username=media.get('username', ''),
                    comment_text='',  # Will be filled when we post the comment
                    commented_at=datetime.utcnow(),
                    was_mentioned=True,
                    engagement_type='mention_response',
                    status='pending'  # Pending comment posting
                )
                db.add(engagement)
                await db.commit()

                # If sample is already completed, we can post the comment immediately
                if existing_sample.status == ProcessingStatus.COMPLETED:
                    # Trigger comment posting (will be implemented in auto-commenting function)
                    logger.info(f"Sample already completed. Triggering immediate comment posting.")
                    # TODO: Trigger Inngest function to post comment
                    pass

                return str(existing_sample.id)

            # Step 6: Create new sample record
            sample = Sample(
                source=SampleSource.INSTAGRAM,
                instagram_shortcode=shortcode,
                instagram_url=permalink,
                status=ProcessingStatus.PENDING,
                creator_id=None  # No user association for mentions (organic/free processing)
            )
            db.add(sample)
            await db.flush()  # Get the sample ID without committing

            # Step 7: Create engagement tracking record
            engagement = InstagramEngagement(
                sample_id=sample.id,
                instagram_media_id=media_id,
                instagram_post_url=permalink,
                instagram_username=media.get('username', ''),
                comment_text='',  # Will be filled when we post the comment
                commented_at=datetime.utcnow(),
                was_mentioned=True,
                engagement_type='mention_response',
                status='pending'  # Pending processing
            )
            db.add(engagement)
            await db.commit()
            await db.refresh(sample)

            logger.info(
                f"Created sample {sample.id} and engagement {engagement.id} "
                f"for Instagram mention (shortcode={shortcode})"
            )

            # Step 8: Trigger Inngest processing pipeline
            await inngest_client.send(
                inngest.Event(
                    name="instagram/video.submitted",
                    data={
                        "sample_id": str(sample.id),
                        "shortcode": shortcode,
                        "url": permalink,
                        "media_id": media_id,
                        "engagement_id": str(engagement.id)
                    }
                )
            )

            logger.info(f"Successfully queued Instagram processing for sample {sample.id}")
            return str(sample.id)

        except Exception as e:
            logger.error(f"Error processing Instagram mention for media_id={media_id}: {str(e)}", exc_info=True)
            await db.rollback()
            return None


async def _create_skipped_engagement(
    db: AsyncSession,
    media_id: str,
    media: dict,
    reason: str
) -> InstagramEngagement:
    """Create an engagement record for skipped content (non-videos, etc.)"""
    engagement = InstagramEngagement(
        sample_id=None,  # No sample created
        instagram_media_id=media_id,
        instagram_post_url=media.get('permalink', ''),
        instagram_username=media.get('username', ''),
        comment_text=f"Skipped: {reason}",
        commented_at=datetime.utcnow(),
        was_mentioned=True,
        engagement_type='mention_skipped',
        status='skipped'
    )
    db.add(engagement)
    return engagement


async def _create_failed_engagement(
    db: AsyncSession,
    media_id: str,
    media: dict,
    reason: str
) -> InstagramEngagement:
    """Create an engagement record for failed processing"""
    engagement = InstagramEngagement(
        sample_id=None,  # No sample created
        instagram_media_id=media_id,
        instagram_post_url=media.get('permalink', ''),
        instagram_username=media.get('username', ''),
        comment_text=f"Failed: {reason}",
        commented_at=datetime.utcnow(),
        was_mentioned=True,
        engagement_type='mention_failed',
        status='failed'
    )
    db.add(engagement)
    return engagement
