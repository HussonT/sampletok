"""
Tests for RapidAPI TikTok downloader integration
"""
import pytest
import tempfile
from pathlib import Path

from app.services.tiktok.downloader import TikTokDownloader


class TestTikTokDownloader:
    """Tests for TikTok video downloader service"""

    @pytest.mark.asyncio
    async def test_get_video_info(self, sample_tiktok_url: str):
        """Test fetching video info without downloading"""
        downloader = TikTokDownloader()

        info = await downloader.get_video_info(sample_tiktok_url)

        # Verify required fields are present
        assert "title" in info
        assert "creator_username" in info
        assert "creator_name" in info
        assert "view_count" in info
        assert "like_count" in info
        assert "comment_count" in info

        # Verify data types
        assert isinstance(info["view_count"], int)
        assert isinstance(info["like_count"], int)
        assert isinstance(info["comment_count"], int)

    @pytest.mark.asyncio
    async def test_download_video(self, sample_tiktok_url: str):
        """Test downloading a video with full metadata"""
        downloader = TikTokDownloader()

        with tempfile.TemporaryDirectory(prefix='tiktok_test_') as temp_dir:
            metadata = await downloader.download_video(sample_tiktok_url, temp_dir)

            # Verify video was downloaded
            video_path = Path(metadata['video_path'])
            assert video_path.exists()
            assert video_path.stat().st_size > 0

            # Verify metadata fields
            assert "aweme_id" in metadata
            assert "title" in metadata
            assert "region" in metadata
            assert "creator_username" in metadata
            assert "creator_name" in metadata
            assert "view_count" in metadata
            assert "like_count" in metadata
            assert "comment_count" in metadata
            assert "upload_timestamp" in metadata

            # Verify URLs
            assert "thumbnail_url" in metadata
            assert "video_url" in metadata or "video_url_watermark" in metadata

    @pytest.mark.asyncio
    async def test_invalid_url_handling(self, invalid_url: str):
        """Test handling of invalid URLs"""
        downloader = TikTokDownloader()

        with pytest.raises(Exception):
            await downloader.get_video_info(invalid_url)

    @pytest.mark.asyncio
    async def test_malformed_url(self):
        """Test handling of malformed URLs"""
        downloader = TikTokDownloader()
        malformed_url = "not-a-url"

        with pytest.raises(Exception):
            await downloader.get_video_info(malformed_url)
