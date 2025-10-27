import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import mimetypes
import logging
from typing import Optional
import aiofiles
import asyncio
import httpx
import tempfile

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Storage:
    """Handle file uploads to S3 or compatible storage"""

    def __init__(self):
        # Configure S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or 'minioadmin',
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or 'minioadmin',
            region_name=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL or 'http://localhost:9000'
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    async def upload_file(self, file_path: str, object_key: str) -> str:
        """
        Upload file to S3 and return public URL
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = 'application/octet-stream'

        try:
            # Read file
            async with aiofiles.open(file_path, 'rb') as f:
                file_data = await f.read()

            # Upload to S3 (run in executor for sync boto3 call)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._upload_to_s3,
                file_data,
                object_key,
                content_type
            )

            # Generate public URL
            url = self.get_public_url(object_key)
            logger.info(f"Successfully uploaded {object_key} to S3")

            return url

        except ClientError as e:
            logger.error(f"S3 upload failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during upload: {str(e)}")
            raise

    def _upload_to_s3(self, file_data: bytes, object_key: str, content_type: str):
        """Synchronous S3/R2 upload"""
        # R2 doesn't support ACL parameter - use bucket-level public access instead
        upload_params = {
            'Bucket': self.bucket_name,
            'Key': object_key,
            'Body': file_data,
            'ContentType': content_type
        }

        # Only add ACL for S3, not for R2
        if settings.STORAGE_TYPE != "r2":
            upload_params['ACL'] = 'public-read'

        self.s3_client.put_object(**upload_params)

    async def download_and_upload_url(self, url: str, object_key: str, content_type: Optional[str] = None) -> Optional[str]:
        """
        Download file from external URL and upload to our storage

        Args:
            url: External URL to download from
            object_key: S3 key to store the file under
            content_type: Optional content type override

        Returns:
            Public URL of uploaded file, or None if download/upload fails
        """
        if not url:
            logger.warning("Empty URL provided to download_and_upload_url")
            return None

        try:
            # Download from external URL
            logger.info(f"Downloading from URL: {url}")
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                file_data = response.content

                # Use response content type if not provided
                if not content_type:
                    content_type = response.headers.get('content-type', 'application/octet-stream')

            # Upload to our storage
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._upload_to_s3,
                file_data,
                object_key,
                content_type
            )

            # Generate and return public URL
            url = self.get_public_url(object_key)
            logger.info(f"Successfully uploaded {object_key} from external URL")
            return url

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading from {url}: {e.response.status_code}")
            return None
        except ClientError as e:
            logger.error(f"S3 upload failed for {object_key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in download_and_upload_url: {str(e)}")
            return None

    async def download_file(self, object_key: str, destination_path: str) -> str:
        """
        Download file from S3
        """
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Download from S3 (run in executor for sync boto3 call)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.s3_client.download_file,
                self.bucket_name,
                object_key,
                str(destination)
            )

            logger.info(f"Successfully downloaded {object_key} from S3")
            return str(destination)

        except ClientError as e:
            logger.error(f"S3 download failed: {str(e)}")
            raise

    async def delete_file(self, object_key: str) -> bool:
        """
        Delete file from S3/R2
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
            )

            logger.info(f"Successfully deleted {object_key} from storage")
            return True

        except ClientError as e:
            logger.error(f"Storage delete failed: {str(e)}")
            return False

    def get_public_url(self, object_key: str) -> str:
        """
        Generate public URL for an S3/R2 object
        """
        # Debug logging to see actual config values
        logger.debug(f"get_public_url called - STORAGE_TYPE={settings.STORAGE_TYPE}, R2_PUBLIC_DOMAIN={settings.R2_PUBLIC_DOMAIN}, object_key={object_key}")

        # Check if using Cloudflare R2
        if settings.STORAGE_TYPE == "r2":
            # Option 1: Use custom domain if configured
            if settings.R2_PUBLIC_DOMAIN:
                logger.info(f"Using R2 public domain: {settings.R2_PUBLIC_DOMAIN}")
                return f"https://{settings.R2_PUBLIC_DOMAIN}/{object_key}"
            # Option 2: Use R2 dev subdomain (requires bucket-level public access)
            # Format: https://pub-{hash}.r2.dev/{object_key}
            # Note: You need to enable R2.dev subdomain in Cloudflare dashboard
            # For now, return the direct endpoint URL (works if bucket is public)
            elif settings.S3_ENDPOINT_URL:
                # Extract account ID from endpoint
                # https://817fde014b86ba18d60b1820218aece1.r2.cloudflarestorage.com
                base_url = settings.S3_ENDPOINT_URL.rstrip('/')
                return f"{base_url}/{self.bucket_name}/{object_key}"

        # For MinIO or custom endpoints
        if settings.S3_ENDPOINT_URL:
            base_url = settings.S3_ENDPOINT_URL.rstrip('/')
            return f"{base_url}/{self.bucket_name}/{object_key}"

        # For AWS S3
        return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{object_key}"

    def generate_presigned_url(self, object_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access
        """
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise

    async def list_files(self, prefix: str = '') -> list:
        """
        List files in S3/R2 bucket with optional prefix
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )
            )

            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })

            return files

        except ClientError as e:
            logger.error(f"Storage list failed: {str(e)}")
            return []