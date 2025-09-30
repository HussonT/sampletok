#!/usr/bin/env python3
"""
Test Cloudflare R2 connection and operations
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.storage.s3 import S3Storage
from app.core.config import settings


async def test_r2_connection():
    """Test R2 connection with upload, download, list, and delete operations"""
    print("=" * 60)
    print("Testing Cloudflare R2 Connection")
    print("=" * 60)
    print(f"\nStorage Type: {settings.STORAGE_TYPE}")
    print(f"Bucket Name: {settings.S3_BUCKET_NAME}")
    print(f"Endpoint URL: {settings.S3_ENDPOINT_URL}")
    print(f"Region: {settings.AWS_REGION}")
    print()

    storage = S3Storage()

    # Test 1: Create a test file
    print("1. Creating test file...")
    test_file_path = Path("/tmp/r2_test.txt")
    test_content = "Hello from SampleTok! Testing R2 storage."
    test_file_path.write_text(test_content)
    print(f"   ✓ Created: {test_file_path}")

    # Test 2: Upload file
    print("\n2. Uploading file to R2...")
    try:
        object_key = "test/r2_test.txt"
        public_url = await storage.upload_file(str(test_file_path), object_key)
        print(f"   ✓ Uploaded successfully")
        print(f"   Public URL: {public_url}")
    except Exception as e:
        print(f"   ✗ Upload failed: {e}")
        return False

    # Test 3: List files
    print("\n3. Listing files in bucket...")
    try:
        files = await storage.list_files(prefix="test/")
        print(f"   ✓ Found {len(files)} file(s) in test/ prefix:")
        for file in files:
            print(f"      - {file['key']} ({file['size']} bytes)")
    except Exception as e:
        print(f"   ✗ List failed: {e}")

    # Test 4: Download file
    print("\n4. Downloading file from R2...")
    try:
        download_path = "/tmp/r2_test_download.txt"
        result = await storage.download_file(object_key, download_path)
        downloaded_content = Path(download_path).read_text()
        if downloaded_content == test_content:
            print(f"   ✓ Downloaded successfully")
            print(f"   Content matches: {downloaded_content}")
        else:
            print(f"   ✗ Content mismatch!")
    except Exception as e:
        print(f"   ✗ Download failed: {e}")

    # Test 5: Delete file
    print("\n5. Deleting test file from R2...")
    try:
        success = await storage.delete_file(object_key)
        if success:
            print(f"   ✓ Deleted successfully")
        else:
            print(f"   ✗ Delete failed")
    except Exception as e:
        print(f"   ✗ Delete error: {e}")

    # Cleanup
    print("\n6. Cleaning up local files...")
    test_file_path.unlink(missing_ok=True)
    Path(download_path).unlink(missing_ok=True)
    print(f"   ✓ Cleaned up")

    print("\n" + "=" * 60)
    print("R2 Connection Test Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. If upload worked but public URL doesn't load:")
    print("   → Enable public access in Cloudflare R2 dashboard")
    print("   → Or set up R2.dev subdomain")
    print("   → Or configure custom domain (R2_PUBLIC_DOMAIN)")
    print("\n2. Test full pipeline: python test_full_pipeline.py")
    print()

    return True


if __name__ == "__main__":
    asyncio.run(test_r2_connection())