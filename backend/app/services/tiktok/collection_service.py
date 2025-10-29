import logging
from typing import Dict, Any, List
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TikTokCollectionService:
    """Service for fetching TikTok user collections using RapidAPI"""

    def __init__(self):
        self.api_key = settings.RAPIDAPI_KEY
        self.api_host = settings.RAPIDAPI_HOST
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.api_host
        }

    async def fetch_collection_list(
        self,
        username: str,
        count: int = None,
        cursor: int = 0
    ) -> Dict[str, Any]:
        """
        Fetch a TikTok user's public collections

        Args:
            username: TikTok username (unique_id)
            count: Number of collections to fetch (uses MAX_COLLECTIONS_PER_REQUEST if not specified)
            cursor: Pagination cursor (default 0)

        Returns:
            Dict with structure:
            {
                "code": 0,
                "msg": "success",
                "processed_time": 0.4362,
                "data": {
                    "collection_list": [
                        {
                            "id": "7565254233776196385",
                            "name": "To sample",
                            "state": 3,
                            "video_count": 21
                        },
                        ...
                    ],
                    "cursor": 2,
                    "hasMore": false
                }
            }
        """
        api_url = f"https://{self.api_host}/collection/list"
        params = {
            "unique_id": username,
            "count": count if count is not None else settings.MAX_COLLECTIONS_PER_REQUEST,
            "cursor": cursor
        }

        try:
            async with httpx.AsyncClient(timeout=float(settings.TIKTOK_API_TIMEOUT_SECONDS)) as client:
                logger.info(f"Fetching collections for user: {username}")
                response = await client.get(api_url, headers=self.headers, params=params)
                response.raise_for_status()

                data = response.json()

                # Validate response structure
                if data.get("code") != 0:
                    error_msg = data.get("msg", "Unknown error")
                    logger.error(f"API returned error: {error_msg}")
                    raise ValueError(f"Failed to fetch collections: {error_msg}")

                logger.info(f"Successfully fetched {len(data.get('data', {}).get('collection_list', []))} collections")
                return data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching collections: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching collections: {str(e)}")
            raise

    async def fetch_collection_posts(
        self,
        collection_id: str,
        count: int = None,
        cursor: int = 0
    ) -> Dict[str, Any]:
        """
        Fetch videos/posts from a specific TikTok collection

        Args:
            collection_id: TikTok collection ID
            count: Number of posts to fetch (uses TIKTOK_API_MAX_PER_REQUEST if not specified)
            cursor: Pagination cursor (default 0)

        Returns:
            Dict with structure:
            {
                "code": 0,
                "msg": "success",
                "processed_time": 0.4362,
                "data": {
                    "videos": [
                        {
                            "aweme_id": "7123456789",
                            "video_id": "7123456789",
                            "title": "Video title",
                            "author": {...},
                            "play": "...",
                            "duration": 60,
                            ...
                        },
                        ...
                    ],
                    "cursor": 30,
                    "hasMore": true
                }
            }
        """
        api_url = f"https://{self.api_host}/collection/posts"
        params = {
            "collection_id": collection_id,
            "count": count if count is not None else settings.TIKTOK_API_MAX_PER_REQUEST,
            "cursor": cursor
        }

        try:
            async with httpx.AsyncClient(timeout=float(settings.TIKTOK_API_TIMEOUT_SECONDS)) as client:
                logger.info(f"Fetching posts for collection: {collection_id}")
                response = await client.get(api_url, headers=self.headers, params=params)
                response.raise_for_status()

                data = response.json()

                # Validate response structure
                if data.get("code") != 0:
                    error_msg = data.get("msg", "Unknown error")
                    logger.error(f"API returned error: {error_msg}")
                    raise ValueError(f"Failed to fetch collection posts: {error_msg}")

                videos = data.get('data', {}).get('videos', [])
                logger.info(f"Successfully fetched {len(videos)} posts from collection")
                return data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching collection posts: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching collection posts: {str(e)}")
            raise

    async def fetch_all_collection_posts(
        self,
        collection_id: str,
        max_videos: int = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all posts from a collection with pagination
        Limits to max_videos (uses MAX_VIDEOS_PER_BATCH if not specified)

        Args:
            collection_id: TikTok collection ID
            max_videos: Maximum number of videos to fetch (uses MAX_VIDEOS_PER_BATCH if not specified)

        Returns:
            List of video data dicts (aweme objects)
        """
        if max_videos is None:
            max_videos = settings.MAX_VIDEOS_PER_BATCH

        all_posts = []
        cursor = 0
        has_more = True

        while has_more and len(all_posts) < max_videos:
            # Calculate how many more we need
            remaining = max_videos - len(all_posts)
            count = min(settings.TIKTOK_API_MAX_PER_REQUEST, remaining)

            try:
                result = await self.fetch_collection_posts(
                    collection_id=collection_id,
                    count=count,
                    cursor=cursor
                )

                data = result.get('data', {})
                aweme_list = data.get('aweme_list', [])

                if not aweme_list:
                    break

                all_posts.extend(aweme_list)

                # Check if there are more posts
                has_more = data.get('hasMore', False)
                cursor = data.get('cursor', cursor + len(aweme_list))

                logger.info(f"Fetched {len(all_posts)} total posts so far")

            except Exception as e:
                logger.error(f"Error during pagination: {str(e)}")
                # Return what we've collected so far
                break

        # Limit to max_videos
        final_posts = all_posts[:max_videos]
        logger.info(f"Returning {len(final_posts)} posts (limit: {max_videos})")
        return final_posts
