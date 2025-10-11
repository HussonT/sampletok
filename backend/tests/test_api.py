"""
Tests for the TikTok processing API endpoints
"""
import pytest
from httpx import AsyncClient


class TestProcessTikTokEndpoint:
    """Tests for the /api/v1/process/tiktok endpoint"""

    @pytest.mark.asyncio
    async def test_process_valid_video(self, client: AsyncClient, sample_tiktok_url: str):
        """Test processing a valid TikTok URL"""
        response = await client.post(
            "/api/v1/process/tiktok",
            json={"url": sample_tiktok_url}
        )

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert "status" in data
        assert "message" in data
        assert data["status"] in ["queued", "processing"]

    @pytest.mark.asyncio
    async def test_process_invalid_url(self, client: AsyncClient, invalid_url: str):
        """Test processing an invalid URL"""
        response = await client.post(
            "/api/v1/process/tiktok",
            json={"url": invalid_url}
        )

        # Should either return 400 or 422 for invalid URL
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_process_missing_url(self, client: AsyncClient):
        """Test processing request without URL"""
        response = await client.post(
            "/api/v1/process/tiktok",
            json={}
        )

        assert response.status_code == 422  # Validation error


class TestStatusEndpoint:
    """Tests for the /api/v1/process/status/{task_id} endpoint"""

    @pytest.mark.asyncio
    async def test_check_status_invalid_task_id(self, client: AsyncClient):
        """Test checking status with invalid task ID"""
        response = await client.get("/api/v1/process/status/invalid-task-id")

        # Should return 404 for non-existent task
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_check_status_valid_flow(
        self,
        client: AsyncClient,
        sample_tiktok_url: str
    ):
        """Test the full flow: submit video and check status"""
        # Submit video for processing
        submit_response = await client.post(
            "/api/v1/process/tiktok",
            json={"url": sample_tiktok_url}
        )

        assert submit_response.status_code == 200
        task_id = submit_response.json()["task_id"]

        # Check status
        status_response = await client.get(f"/api/v1/process/status/{task_id}")

        assert status_response.status_code == 200
        status_data = status_response.json()

        assert status_data["task_id"] == task_id
        assert "status" in status_data
        assert "progress" in status_data
        assert "message" in status_data
