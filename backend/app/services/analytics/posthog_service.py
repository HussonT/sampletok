"""
PostHog Analytics Service for Backend Event Tracking

This service provides a centralized way to track events in PostHog from the backend.
It automatically handles initialization, error handling, and event flushing for
serverless/Cloud Run environments.

Usage:
    from app.services.analytics.posthog_service import posthog_service

    # Track an event
    posthog_service.track_event(
        user_id="clerk_user_123",
        event="sample_processed",
        properties={
            "sample_id": "abc123",
            "processing_time_seconds": 5.2,
        }
    )

    # Identify a user
    posthog_service.identify_user(
        user_id="clerk_user_123",
        properties={
            "email": "user@example.com",
            "name": "John Doe",
        }
    )

    # Always flush events at end of request (handled by middleware)
    posthog_service.flush()
"""

import posthog
from typing import Optional, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class PostHogService:
    """
    PostHog analytics service for backend event tracking.

    Handles initialization, event tracking, user identification, and proper
    event flushing for serverless environments.
    """

    def __init__(self):
        """Initialize PostHog with project credentials."""
        self.enabled = False

        if settings.POSTHOG_PROJECT_KEY:
            try:
                posthog.project_api_key = settings.POSTHOG_PROJECT_KEY
                posthog.host = settings.POSTHOG_HOST or "https://eu.posthog.com"
                posthog.debug = settings.ENVIRONMENT == "development"
                self.enabled = True
                logger.info(f"PostHog initialized (host: {posthog.host}, debug: {posthog.debug})")
            except Exception as e:
                logger.error(f"Failed to initialize PostHog: {e}")
                self.enabled = False
        else:
            logger.warning("PostHog not configured (POSTHOG_PROJECT_KEY missing) - analytics disabled")

    def track_event(
        self,
        event: str,
        user_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        distinct_id: Optional[str] = None,
    ):
        """
        Track an event in PostHog.

        Args:
            event: Event name (e.g., "sample_processed")
            user_id: Clerk user ID (if authenticated)
            properties: Event properties/metadata
            distinct_id: Override distinct_id (default: user_id or "anonymous")

        Example:
            posthog_service.track_event(
                event="tiktok_processing_completed",
                user_id="user_123",
                properties={
                    "sample_id": "abc",
                    "processing_time": 5.2,
                    "bpm": 120,
                }
            )
        """
        if not self.enabled:
            return

        try:
            distinct_id = distinct_id or user_id or "anonymous"
            properties = properties or {}

            # Add system context to all events
            properties["environment"] = settings.ENVIRONMENT
            properties["source"] = "backend"

            posthog.capture(
                distinct_id=distinct_id,
                event=event,
                properties=properties,
            )

            logger.debug(f"PostHog event tracked: {event} (distinct_id: {distinct_id})")

        except Exception as e:
            logger.error(f"Failed to track PostHog event '{event}': {e}")

    def identify_user(
        self,
        user_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ):
        """
        Identify a user with additional properties.

        Args:
            user_id: Clerk user ID
            properties: User properties (email, name, subscription, etc.)

        Example:
            posthog_service.identify_user(
                user_id="user_123",
                properties={
                    "email": "user@example.com",
                    "name": "John Doe",
                    "subscription_tier": "pro",
                }
            )
        """
        if not self.enabled:
            return

        try:
            posthog.identify(
                distinct_id=user_id,
                properties=properties or {},
            )

            logger.debug(f"PostHog user identified: {user_id}")

        except Exception as e:
            logger.error(f"Failed to identify user in PostHog: {e}")

    def group_identify(
        self,
        group_type: str,
        group_key: str,
        properties: Optional[Dict[str, Any]] = None,
    ):
        """
        Identify a group (e.g., company, team) in PostHog.

        Args:
            group_type: Type of group (e.g., "company", "team")
            group_key: Unique identifier for the group
            properties: Group properties

        Example:
            posthog_service.group_identify(
                group_type="subscription_tier",
                group_key="pro",
                properties={"tier_name": "Professional"}
            )
        """
        if not self.enabled:
            return

        try:
            posthog.group_identify(
                group_type=group_type,
                group_key=group_key,
                properties=properties or {},
            )

            logger.debug(f"PostHog group identified: {group_type}:{group_key}")

        except Exception as e:
            logger.error(f"Failed to identify group in PostHog: {e}")

    def flush(self):
        """
        Force flush events to PostHog.

        CRITICAL for serverless/Cloud Run environments where the process may
        terminate before events are sent. Should be called at the end of each
        request (handled by middleware).
        """
        if not self.enabled:
            return

        try:
            posthog.flush()
            logger.debug("PostHog events flushed")

        except Exception as e:
            logger.error(f"Failed to flush PostHog events: {e}")

    def shutdown(self):
        """
        Shutdown PostHog client and flush remaining events.

        Should be called during application shutdown.
        """
        if not self.enabled:
            return

        try:
            posthog.shutdown()
            logger.info("PostHog client shutdown")

        except Exception as e:
            logger.error(f"Failed to shutdown PostHog client: {e}")


# Singleton instance
posthog_service = PostHogService()
