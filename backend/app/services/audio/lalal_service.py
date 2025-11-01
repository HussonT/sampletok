import asyncio
import json
import logging
import httpx
from pathlib import Path
from typing import Dict, List, Optional
import os

from app.core.config import settings
from app.services.audio.exceptions import (
    LalalAIException,
    LalalAPIKeyError,
    LalalRateLimitError,
    LalalQuotaExceededError,
    LalalFileError,
    LalalProcessingError,
    LalalTimeoutError
)

logger = logging.getLogger(__name__)


class LalalAIService:
    """Service for interacting with La La AI stem separation API"""

    BASE_URL = "https://www.lalal.ai/api"

    def __init__(self):
        self.api_key = settings.LALAL_API_KEY
        if not self.api_key:
            raise ValueError("LALAL_API_KEY environment variable is required")

        self.headers = {
            "Authorization": f"license {self.api_key}"
        }

    def _parse_http_error(self, error: httpx.HTTPError) -> LalalAIException:
        """
        Parse HTTP errors from La La AI API and return appropriate custom exception.

        Args:
            error: HTTPError from httpx

        Returns:
            Appropriate LalalAIException subclass
        """
        status_code = None
        response_body = None

        if hasattr(error, 'response') and error.response:
            status_code = error.response.status_code
            try:
                response_body = error.response.text
                response_json = error.response.json()
                error_message = response_json.get('error', str(error))
            except Exception:
                error_message = response_body or str(error)
        else:
            error_message = str(error)

        # Map status codes to specific exceptions
        if status_code == 401 or status_code == 403:
            return LalalAPIKeyError(f"Authentication failed: {error_message}")
        elif status_code == 429:
            retry_after = None
            if hasattr(error, 'response') and error.response:
                retry_after = error.response.headers.get('Retry-After')
            return LalalRateLimitError(error_message, retry_after=retry_after)
        elif status_code == 402:
            return LalalQuotaExceededError(error_message)
        elif status_code == 400:
            return LalalFileError(error_message, status_code=400)
        elif status_code == 413:
            return LalalFileError("File size exceeds maximum allowed", status_code=413)
        elif status_code == 504 or status_code == 408:
            return LalalTimeoutError(error_message)
        elif status_code and status_code >= 500:
            return LalalProcessingError(f"La La AI server error: {error_message}", status_code=status_code)
        else:
            return LalalAIException(error_message, status_code=status_code, response_body=response_body)

    async def upload_file(self, file_path: str) -> str:
        """
        Upload a file to La La AI
        Returns: file_id for use in separation request
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size (max 1GB without license, 10GB with license)
        file_size = file_path.stat().st_size
        max_size = 10 * 1024 * 1024 * 1024  # 10GB assuming license

        if file_size > max_size:
            raise ValueError(f"File size {file_size} exceeds maximum {max_size}")

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Read file as binary data
                with open(file_path, 'rb') as f:
                    file_content = f.read()

                # Lalal.ai requires Content-Disposition header with filename
                # Try ASCII encoding first, fall back to UTF-8 if needed
                try:
                    filename = file_path.name.encode('ascii').decode('ascii')
                    content_disposition = f'attachment; filename="{filename}"'
                except UnicodeEncodeError:
                    # Use RFC 5987 encoding for non-ASCII filenames
                    from urllib.parse import quote
                    filename_utf8 = quote(file_path.name)
                    content_disposition = f"attachment; filename*=utf-8''{filename_utf8}"

                # Merge Content-Disposition with existing headers
                upload_headers = {
                    **self.headers,
                    "Content-Disposition": content_disposition
                }

                logger.info(f"Uploading file: {file_path.name} (size: {len(file_content)} bytes)")

                response = await client.post(
                    f"{self.BASE_URL}/upload/",
                    headers=upload_headers,
                    content=file_content  # Send as binary data, not multipart
                )

                response.raise_for_status()
                data = response.json()

                if data.get('status') != 'success':
                    error_msg = data.get('error', 'Unknown error')
                    raise LalalFileError(f"Upload failed: {error_msg}")

                file_id = data.get('id')
                logger.info(f"Successfully uploaded file to La La AI: {file_id}")
                return file_id

        except httpx.TimeoutException as e:
            logger.error(f"Timeout uploading file to La La AI: {str(e)}")
            raise LalalTimeoutError("File upload timed out")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error uploading file to La La AI: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise self._parse_http_error(e)
        except LalalAIException:
            # Re-raise custom exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file to La La AI: {str(e)}")
            raise LalalProcessingError(f"File upload failed: {str(e)}")

    async def submit_separation(
        self,
        file_id: str,
        stem_types: List[str],
        splitter_type: str = "phoenix"  # phoenix, orion, or perseus
    ) -> Dict[str, str]:
        """
        Submit a stem separation job

        Args:
            file_id: File ID from upload
            stem_types: List of stem types to extract (e.g., ["vocals", "drum", "bass"])
            splitter_type: Neural network model to use (phoenix has most stems)

        Returns: Dict with 'file_id' and 'task_id' (comma-separated if multiple)
        """
        try:
            # Map our stem types to La La AI expected format
            # Note: Lalal.ai uses 'vocals' (plural) not 'vocal' (singular)
            stem_mapping = {
                'vocal': 'vocals',
                'vocals': 'vocals',
                'voice': 'voice',
                'drum': 'drum',
                'drums': 'drum',
                'piano': 'piano',
                'bass': 'bass',
                'electric_guitar': 'electric_guitar',
                'acoustic_guitar': 'acoustic_guitar',
                'synthesizer': 'synthesizer',
                'strings': 'strings',
                'wind': 'wind'
            }

            # Convert to La La AI format and create params array
            params = []
            for stem in stem_types:
                mapped_stem = stem_mapping.get(stem.lower(), stem)
                params.append({
                    "id": file_id,
                    "splitter": splitter_type,
                    "stem": mapped_stem
                })

            async with httpx.AsyncClient(timeout=60.0) as client:
                # La La AI split endpoint expects a 'params' form field with JSON-encoded array
                payload = {
                    "params": json.dumps(params)
                }

                logger.info(f"Submitting separation: file_id={file_id}, splitter={splitter_type}, stems={stem_types}")
                logger.debug(f"Params payload: {payload}")

                response = await client.post(
                    f"{self.BASE_URL}/split/",
                    headers=self.headers,
                    data=payload  # Use form data with JSON-encoded params
                )

                response.raise_for_status()
                data = response.json()

                logger.info(f"La La AI split response: {data}")

                if data.get('status') != 'success':
                    error_msg = data.get('error', 'Unknown error')
                    logger.error(f"Split submission failed: {error_msg}")
                    raise LalalProcessingError(f"Split submission failed: {error_msg}")

                # API returns 'task_id' as comma-separated string (optional field)
                task_id = data.get('task_id', '')

                logger.info(f"Successfully submitted separation job for file_id={file_id}, task_ids={task_id}")

                # Return both file_id (needed for checking) and task_id (optional, for reference)
                return {
                    'file_id': file_id,
                    'task_id': task_id
                }

        except httpx.TimeoutException as e:
            logger.error(f"Timeout submitting separation to La La AI: {str(e)}")
            raise LalalTimeoutError("Stem separation submission timed out")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error submitting separation to La La AI: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise self._parse_http_error(e)
        except LalalAIException:
            # Re-raise custom exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error submitting separation to La La AI: {str(e)}")
            raise LalalProcessingError(f"Stem separation submission failed: {str(e)}")

    async def check_task_status(self, file_id: str) -> Dict:
        """
        Check the status of a separation task using file_id

        Args:
            file_id: File ID from upload (NOT task_id)

        Returns dict with:
        - status: 'processing', 'completed', 'failed'
        - result_urls: dict of stem_type -> download_url (when completed)
        - error: error message (if failed)
        - raw_result: full result dict from API (for debugging)
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Pass file_id (not task_id) to check endpoint
                payload = {"id": file_id}

                response = await client.post(
                    f"{self.BASE_URL}/check/",
                    headers=self.headers,
                    data=payload
                )

                response.raise_for_status()
                data = response.json()

                logger.debug(f"Check file status response for {file_id}: {data}")

                if data.get('status') == 'error':
                    error_msg = data.get('error', 'Unknown error')
                    logger.error(f"Check failed for file {file_id}: {error_msg}")
                    return {
                        'status': 'failed',
                        'error': error_msg
                    }

                # Result is keyed by file_id
                result_dict = data.get('result', {})
                file_result = result_dict.get(file_id)

                if not file_result:
                    logger.error(f"No result for file_id {file_id} in response: {data}")
                    return {
                        'status': 'failed',
                        'error': f'No result found for file_id {file_id}'
                    }

                # Check file-level status first
                if file_result.get('status') == 'error':
                    error_msg = file_result.get('error', 'Unknown error')
                    logger.error(f"File {file_id} error: {error_msg}")
                    return {
                        'status': 'failed',
                        'error': error_msg
                    }

                # Check task state (nested under file_result)
                task_info = file_result.get('task')

                if not task_info:
                    # No task info means file uploaded but not yet split
                    return {
                        'status': 'processing'
                    }

                task_state = task_info.get('state')
                logger.debug(f"File {file_id} task state: {task_state}")

                if task_state == 'success':
                    # Task completed successfully
                    # Split URLs are in file_result.split object
                    split_data = file_result.get('split', {})

                    result_urls = {}

                    # La La AI returns:
                    # - stem_track: URL for the extracted stem
                    # - back_track: URL for the background/instrumental
                    if split_data.get('stem_track'):
                        # Extract stem name from file_result or use generic 'stem'
                        stem_name = file_result.get('stem', 'stem')
                        result_urls[stem_name] = split_data['stem_track']

                    if split_data.get('back_track'):
                        result_urls['background'] = split_data['back_track']

                    logger.info(f"File {file_id} completed with {len(result_urls)} result URLs")

                    return {
                        'status': 'completed',
                        'result_urls': result_urls,
                        'raw_result': file_result  # Include for debugging
                    }
                elif task_state == 'progress':
                    # Task is still processing
                    progress = task_info.get('progress', 0)
                    logger.debug(f"File {file_id} progress: {progress}%")
                    return {
                        'status': 'processing',
                        'progress': progress
                    }
                elif task_state in ['error', 'cancelled']:
                    error_msg = task_info.get('error') or file_result.get('error') or 'Processing failed'
                    return {
                        'status': 'failed',
                        'error': error_msg
                    }
                else:
                    # Unknown state, assume still processing
                    logger.warning(f"Unknown task state for file {file_id}: {task_state}")
                    return {
                        'status': 'processing'
                    }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error checking task status: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error checking task status: {str(e)}")
            raise

    async def download_file(self, url: str, output_path: str) -> str:
        """
        Download a separated stem file
        Returns: path to downloaded file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                with open(output_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"Successfully downloaded stem to: {output_path}")
                return str(output_path)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error downloading file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise

    async def poll_until_complete(
        self,
        file_id: str,
        max_wait_seconds: int = 600,
        poll_interval: int = 5
    ) -> Dict:
        """
        Poll task status until completion or timeout

        Args:
            file_id: File ID from upload (NOT task_id)
            max_wait_seconds: Maximum time to wait (default 10 minutes)
            poll_interval: Seconds between polls (default 5 seconds)

        Returns: Final task status dict
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time

            if elapsed > max_wait_seconds:
                raise TimeoutError(f"File {file_id} did not complete within {max_wait_seconds} seconds")

            status = await self.check_task_status(file_id)

            if status['status'] in ['completed', 'failed']:
                return status

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def process_stem_separation(
        self,
        audio_file_path: str,
        stem_types: List[str],
        output_dir: str
    ) -> Dict[str, str]:
        """
        High-level method to handle full stem separation workflow

        Args:
            audio_file_path: Path to audio file to process
            stem_types: List of stem types to extract
            output_dir: Directory to save separated stems

        Returns: Dict mapping stem_type to downloaded file path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Upload file
        logger.info(f"Uploading file: {audio_file_path}")
        file_id = await self.upload_file(audio_file_path)

        # Submit separation job
        logger.info(f"Submitting separation for stems: {stem_types}")
        submit_result = await self.submit_separation(file_id, stem_types)

        # submit_result contains file_id and task_id
        file_id = submit_result['file_id']
        task_id = submit_result.get('task_id', 'N/A')
        logger.info(f"Submitted job - file_id: {file_id}, task_id: {task_id}")

        # Poll until complete (using file_id)
        logger.info(f"Polling for completion of file: {file_id}")
        result = await self.poll_until_complete(file_id)

        if result['status'] == 'failed':
            raise Exception(f"Stem separation failed: {result.get('error')}")

        # Download results
        result_urls = result.get('result_urls', {})
        downloaded_files = {}

        for stem_type, url in result_urls.items():
            if url:
                output_path = output_dir / f"{stem_type}.wav"
                await self.download_file(url, str(output_path))
                downloaded_files[stem_type] = str(output_path)

        logger.info(f"Successfully completed stem separation: {len(downloaded_files)} files")
        return downloaded_files
