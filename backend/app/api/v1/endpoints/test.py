"""
Test endpoints for quick verification
"""
from fastapi import APIRouter, HTTPException
import inngest
# Inngest client import removed - functions defined in inngest_functions.py
from app.models.schemas import ProcessingTaskResponse

router = APIRouter()


@router.post("/test-inngest", response_model=ProcessingTaskResponse)
async def test_inngest():
    """
    Test Inngest event sending without database
    """
    try:
        # Send a test event to Inngest
        from app.inngest_functions import inngest_client
        await inngest_client.send(
            inngest.Event(
                name="test/hello",
                data={"message": "Testing Inngest connection"}
            )
        )

        return ProcessingTaskResponse(
            task_id="test-123",
            status="sent",
            message="Test event sent to Inngest successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-connection")
async def test_connection():
    """
    Simple endpoint to test if API is running
    """
    return {
        "status": "ok",
        "message": "Backend is running!",
        "endpoints": {
            "process_tiktok": "POST /api/v1/process/tiktok",
            "get_samples": "GET /api/v1/samples",
            "check_status": "GET /api/v1/process/status/{task_id}"
        }
    }


@router.get("/test-storage-config")
async def test_storage_config():
    """
    Debug endpoint to check storage configuration
    """
    from app.core.config import settings
    return {
        "storage_type": settings.STORAGE_TYPE,
        "r2_public_domain": settings.R2_PUBLIC_DOMAIN,
        "s3_endpoint_url": settings.S3_ENDPOINT_URL,
        "s3_bucket_name": settings.S3_BUCKET_NAME,
        "environment": settings.ENVIRONMENT
    }


# Test Inngest function moved to app.inngest_functions