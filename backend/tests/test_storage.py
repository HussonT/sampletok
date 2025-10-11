"""
Tests for storage (S3/R2) operations
"""
import pytest
from pathlib import Path
import tempfile

from app.services.storage.s3 import S3Storage


class TestS3Storage:
    """Tests for S3/R2 storage service"""

    @pytest.fixture
    def storage(self):
        """Create a storage instance"""
        return S3Storage()

    @pytest.fixture
    def test_file(self):
        """Create a temporary test file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello from SampleTok! Testing storage.")
            test_path = f.name

        yield test_path

        # Cleanup
        Path(test_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_upload_file(self, storage: S3Storage, test_file: str):
        """Test uploading a file to storage"""
        object_key = "test/pytest_test.txt"

        try:
            public_url = await storage.upload_file(test_file, object_key)

            assert public_url is not None
            assert isinstance(public_url, str)
            assert len(public_url) > 0

        finally:
            # Cleanup: delete the uploaded file
            await storage.delete_file(object_key)

    @pytest.mark.asyncio
    async def test_list_files(self, storage: S3Storage, test_file: str):
        """Test listing files in storage"""
        object_key = "test/pytest_list_test.txt"

        try:
            # Upload a test file
            await storage.upload_file(test_file, object_key)

            # List files
            files = await storage.list_files(prefix="test/")

            assert isinstance(files, list)
            assert len(files) > 0
            assert any(f['key'] == object_key for f in files)

        finally:
            # Cleanup
            await storage.delete_file(object_key)

    @pytest.mark.asyncio
    async def test_download_file(self, storage: S3Storage, test_file: str):
        """Test downloading a file from storage"""
        object_key = "test/pytest_download_test.txt"
        download_path = "/tmp/pytest_download_test.txt"

        try:
            # Upload test file
            await storage.upload_file(test_file, object_key)

            # Download it back
            result = await storage.download_file(object_key, download_path)

            assert result is True
            assert Path(download_path).exists()

            # Verify content matches
            original_content = Path(test_file).read_text()
            downloaded_content = Path(download_path).read_text()
            assert original_content == downloaded_content

        finally:
            # Cleanup
            await storage.delete_file(object_key)
            Path(download_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_delete_file(self, storage: S3Storage, test_file: str):
        """Test deleting a file from storage"""
        object_key = "test/pytest_delete_test.txt"

        # Upload test file
        await storage.upload_file(test_file, object_key)

        # Delete it
        success = await storage.delete_file(object_key)

        assert success is True

        # Verify it's gone by listing
        files = await storage.list_files(prefix="test/")
        assert not any(f['key'] == object_key for f in files)

    @pytest.mark.asyncio
    async def test_upload_nonexistent_file(self, storage: S3Storage):
        """Test uploading a file that doesn't exist"""
        with pytest.raises(Exception):
            await storage.upload_file("/nonexistent/file.txt", "test/should_fail.txt")
