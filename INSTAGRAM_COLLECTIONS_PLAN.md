# Instagram Collections Implementation Plan

## Overview
Implement Instagram saved collection import with feature parity to the existing TikTok collection system, using `gallery-dl` for downloading and metadata extraction.

## Architecture Mapping

### URL Format Comparison
- **TikTok**: `https://www.tiktok.com/@username/collection/12345`
- **Instagram**: `https://www.instagram.com/username/saved/vision-board/18257620222217621/`

Both use collection IDs for identification, making the architecture highly compatible.

---

## Implementation Components

### 1. Database Schema (Reuse Existing)
**No changes needed** - Reuse existing `collections` and `collection_samples` tables:
- Replace `tiktok_collection_id` → generic `platform_collection_id`
- Add `platform` enum field: `tiktok` | `instagram`
- All pagination fields (`current_cursor`, `next_cursor`, `has_more`) work for both platforms

**Migration**: Add platform discrimination and rename fields for platform-agnostic naming.

---

### 2. New Service: `InstagramCollectionService`
**File**: `backend/app/services/instagram/collection_service.py`

**Key Methods**:
```python
class InstagramCollectionService:
    def __init__(self, cookies_file: str):
        """Initialize with user's Instagram session cookies"""

    async def fetch_collection_metadata(self, collection_url: str) -> dict:
        """
        Extract collection name and ID from URL
        Returns: {collection_id, collection_name, username}
        """

    async def fetch_collection_posts(
        self,
        collection_url: str,
        max_id: str = None,
        limit: int = 50
    ) -> dict:
        """
        Call gallery-dl with --dump-json to get post metadata
        Returns: {posts: [...], next_cursor: str, has_more: bool}
        """

    async def download_and_extract_media(self, post_url: str) -> dict:
        """
        Download single Instagram post (video/image)
        Returns: {file_path, metadata, thumbnail_url, ...}
        """
```

**Technical Implementation**:
- Wrap `gallery-dl` CLI using Python `subprocess`
- Use `--dump-json` flag for metadata extraction
- Use `--cookies` for authentication
- Parse JSON output to extract post data
- Handle rate limiting with exponential backoff

---

### 3. Gallery-DL Integration Layer
**File**: `backend/app/services/instagram/gallery_dl_wrapper.py`

**Core Functionality**:
```python
class GalleryDLWrapper:
    async def get_collection_posts(
        self,
        url: str,
        cookies_file: str,
        start_index: int = 0,
        count: int = 50
    ) -> dict:
        """
        Execute: gallery-dl --dump-json --cookies <file> --range 0-50 <url>
        Parse JSON lines output
        """

    async def download_post_media(
        self,
        url: str,
        output_dir: str,
        cookies_file: str
    ) -> list[str]:
        """
        Download media files for a single post
        Returns list of downloaded file paths
        """
```

**Command Examples**:
```bash
# Get metadata only (no download)
gallery-dl --dump-json --cookies cookies.txt --range 0-50 \
  "https://www.instagram.com/user/saved/collection/12345/"

# Download specific post
gallery-dl --cookies cookies.txt --dest /tmp/instagram \
  "https://www.instagram.com/p/ABC123/"
```

---

### 4. Modified Models
**File**: `backend/app/models/collection.py`

**Changes**:
```python
class Collection(Base):
    platform = Column(Enum("tiktok", "instagram"), nullable=False, default="tiktok")
    platform_collection_id = Column(String, index=True)  # Renamed from tiktok_collection_id
    platform_username = Column(String, index=True)       # Renamed from tiktok_username

    # Add Instagram-specific fields
    instagram_user_cookies = Column(Text, nullable=True)  # Encrypted session cookies
```

---

### 5. New API Endpoints
**File**: `backend/app/api/v1/endpoints/collections.py`

**New Routes**:

#### `POST /api/v1/collections/instagram/upload-cookies`
```python
{
  "cookies": "sessionid=...; csrftoken=...",  # Instagram session cookies
  "encrypted": true
}
# Store encrypted cookies for user
# Returns: {status: "success", expires_at: "2025-02-01"}
```

#### `POST /api/v1/collections/instagram/validate`
```python
{
  "collection_url": "https://www.instagram.com/user/saved/name/12345/"
}
# Validate URL format and extract metadata
# Returns: {collection_id, collection_name, username, estimated_count}
```

#### `POST /api/v1/collections/instagram/process`
```python
{
  "collection_url": "https://www.instagram.com/user/saved/name/12345/",
  "collection_id": "18257620222217621",
  "collection_name": "vision-board",
  "username": "hussontomm"
}
# Same flow as TikTok: validate, deduct credits, trigger Inngest
```

---

### 6. Inngest Processing Pipeline
**File**: `backend/app/inngest_functions.py`

**New Function**: `process_instagram_collection(ctx)`

**Flow** (mirrors TikTok):
```
1. Fetch collection from DB
2. Update status to "processing"
3. Call gallery-dl to get batch of posts (50 per batch)
4. Parse JSON metadata for each post
5. Filter out already-processed posts
6. For each NEW post:
   a. Download media using gallery-dl
   b. Extract video/audio (reuse existing AudioProcessor)
   c. Generate waveform, analyze BPM/key
   d. Upload to storage (S3/R2/GCS)
   e. Create Sample record
   f. Link via CollectionSample
   g. Refund credit if fails
7. Update processed_count
8. If has_more: trigger next batch
9. On completion: mark collection as completed
10. On error: refund unprocessed credits, mark as failed
```

**Differences from TikTok**:
- Use gallery-dl subprocess instead of HTTP API
- Handle Instagram's rate limiting (sleep between requests)
- Parse gallery-dl JSON output format
- Support both video and image posts (TikTok is video-only)

---

### 7. Cookie Management System
**File**: `backend/app/services/instagram/cookie_manager.py`

**Security Requirements**:
- Encrypt cookies at rest using `cryptography.fernet`
- Store per-user in database (`user.instagram_cookies_encrypted`)
- Validate cookies before processing (test API call)
- Detect expired sessions and notify user
- Never log or expose cookies in responses

**Cookie Validation**:
```python
async def validate_instagram_cookies(cookies: str) -> bool:
    """Test cookies by fetching user's own profile"""
    result = await gallery_dl_wrapper.test_authentication(cookies)
    return result.success
```

---

### 8. Frontend Changes
**Files**:
- `frontend/app/components/features/instagram-collection-form.tsx`
- `frontend/app/components/features/cookie-upload-modal.tsx`

**User Flow**:
1. **Cookie Setup** (one-time):
   - User clicks "Add Instagram Account"
   - Modal shows instructions to export cookies (browser extension)
   - User uploads cookies.txt file
   - Backend validates and stores encrypted

2. **Collection Import**:
   - User pastes Instagram collection URL
   - Frontend validates format
   - Shows preview (collection name, estimated count)
   - User clicks "Import" → credits deducted
   - Shows progress bar (real-time status polling)
   - Redirects to collection page when completed

---

### 9. Credit System (No Changes)
**Reuse existing logic**:
- 1 credit per valid post (same as TikTok)
- Upfront deduction with validation
- Per-post refunds on failure
- Atomic operations with database locks

---

### 10. Configuration
**File**: `backend/app/core/config.py`

**New Settings**:
```python
# Instagram-specific
INSTAGRAM_COOKIES_ENCRYPTION_KEY = os.getenv("INSTAGRAM_COOKIES_KEY")
INSTAGRAM_RATE_LIMIT_PER_MINUTE = 30  # Conservative to avoid bans
INSTAGRAM_POSTS_PER_BATCH = 50
INSTAGRAM_REQUEST_DELAY_SECONDS = 2  # Between API calls

# gallery-dl
GALLERY_DL_PATH = os.getenv("GALLERY_DL_PATH", "gallery-dl")
GALLERY_DL_TIMEOUT_SECONDS = 300  # 5 min for large collections
```

---

## Implementation Phases

### Phase 1: Core Infrastructure
1. Install gallery-dl in backend Docker image
2. Create `GalleryDLWrapper` with basic commands
3. Test gallery-dl Instagram authentication
4. Implement cookie encryption/storage

### Phase 2: Service Layer
1. Create `InstagramCollectionService`
2. Implement metadata fetching (--dump-json)
3. Implement media downloading
4. Add error handling and retries
5. Write unit tests

### Phase 3: Database & Models
1. Create migration to add `platform` field
2. Rename fields for platform-agnostic naming
3. Add `instagram_cookies_encrypted` to User model
4. Update existing queries to be platform-aware

### Phase 4: API & Processing
1. Add new Instagram collection endpoints
2. Implement cookie upload/validation
3. Create `process_instagram_collection` Inngest function
4. Add collection validation logic
5. Test end-to-end with real Instagram data

### Phase 5: Frontend
1. Build cookie upload UI with instructions
2. Create Instagram collection form
3. Add collection preview
4. Implement real-time progress tracking
5. Add error handling and user feedback

### Phase 6: Testing & Polish
1. Test with various collection sizes
2. Test rate limiting behavior
3. Handle edge cases (deleted posts, private accounts)
4. Add admin tools for stuck collections
5. Documentation and deployment

---

## Key Differences from TikTok

| Aspect | TikTok | Instagram |
|--------|--------|-----------|
| **API Access** | Direct HTTP (RapidAPI) | CLI wrapper (gallery-dl) |
| **Authentication** | API key | User session cookies |
| **Rate Limits** | RapidAPI limits | Instagram rate limits (stricter) |
| **Media Types** | Videos only | Videos + Images |
| **Public Access** | Yes (any user's collection) | No (requires user's own cookies) |
| **Pagination** | Cursor-based JSON | gallery-dl handles internally |
| **Metadata Format** | TikTok API JSON | gallery-dl JSON |

---

## Risks & Mitigations

### Risk 1: Instagram Rate Limiting
**Impact**: Account bans, failed imports
**Mitigation**:
- Conservative rate limits (30 req/min)
- Exponential backoff on errors
- Sleep delays between requests
- Detect and handle 429 errors gracefully

### Risk 2: Cookie Expiration
**Impact**: Mid-import failures
**Mitigation**:
- Validate cookies before starting
- Detect auth errors during processing
- Notify user to refresh cookies
- Pause (not fail) collection on auth error

### Risk 3: gallery-dl Breaking Changes
**Impact**: Import failures after updates
**Mitigation**:
- Pin specific gallery-dl version in requirements.txt
- Test updates in staging before production
- Monitor gallery-dl GitHub for breaking changes
- Have fallback to direct Instagram API if needed

### Risk 4: Cookie Security
**Impact**: User account compromise
**Mitigation**:
- Encrypt cookies with Fernet (AES-128)
- Store encryption key in Secret Manager
- Never log cookies
- Rotate encryption keys periodically
- Clear cookies on user request

---

## Success Criteria
- [ ] Users can import Instagram saved collections via URL
- [ ] Processing matches TikTok feature parity (batching, progress, errors)
- [ ] Cookie management is secure and user-friendly
- [ ] Rate limiting prevents account bans
- [ ] Credit system works identically to TikTok
- [ ] Admin tools support Instagram collections
- [ ] Frontend UX matches TikTok collection flow

---

## Estimated Effort
- **Backend**: 3-4 days
- **Frontend**: 2 days
- **Testing**: 2 days
- **Total**: ~7-8 days for full implementation

---

## Alternative: Instaloader
If gallery-dl proves problematic, consider `instaloader` as an alternative:
- Python-native (no subprocess)
- Better Instagram support
- Command: `instaloader :saved` for all saved posts
- May have better error handling

However, gallery-dl is preferred because:
- More actively maintained
- Better JSON output format
- Supports more platforms (future extensibility)
- Proven community support

---

## Technical Deep Dive: gallery-dl Integration

### gallery-dl Command Reference

#### Fetch Collection Metadata Only
```bash
gallery-dl \
  --dump-json \
  --no-download \
  --cookies /path/to/cookies.txt \
  "https://www.instagram.com/hussontomm/saved/vision-board/18257620222217621/"
```

Output format (one JSON object per line):
```json
{
  "category": "instagram",
  "subcategory": "collection",
  "collection_id": "18257620222217621",
  "collection_name": "vision-board",
  "shortcode": "ABC123xyz",
  "post_id": "123456789",
  "post_url": "https://www.instagram.com/p/ABC123xyz/",
  "typename": "GraphVideo",
  "owner": {
    "username": "creator_username",
    "id": "987654321"
  },
  "caption": "Post caption text...",
  "like_count": 1234,
  "comment_count": 56,
  "taken_at_timestamp": 1704067200,
  "video_url": "https://...",
  "thumbnail_url": "https://...",
  "display_url": "https://...",
  "dimensions": {"height": 1920, "width": 1080}
}
```

#### Download Single Post
```bash
gallery-dl \
  --cookies /path/to/cookies.txt \
  --dest /tmp/instagram \
  "https://www.instagram.com/p/ABC123xyz/"
```

#### Pagination Handling
Gallery-dl handles pagination internally. For cursor-based control:
```bash
gallery-dl \
  --dump-json \
  --no-download \
  --cookies /path/to/cookies.txt \
  --range 1-50 \  # First 50 posts
  "https://www.instagram.com/hussontomm/saved/vision-board/18257620222217621/"

gallery-dl \
  --dump-json \
  --no-download \
  --cookies /path/to/cookies.txt \
  --range 51-100 \  # Next 50 posts
  "https://www.instagram.com/hussontomm/saved/vision-board/18257620222217621/"
```

### Python Integration Example

```python
import asyncio
import json
import subprocess
from typing import AsyncIterator

class GalleryDLWrapper:
    def __init__(self, cookies_file: str, timeout: int = 300):
        self.cookies_file = cookies_file
        self.timeout = timeout

    async def fetch_collection_metadata(
        self,
        collection_url: str,
        start: int = 0,
        count: int = 50
    ) -> AsyncIterator[dict]:
        """
        Fetch metadata for posts in a collection
        Yields one post metadata dict at a time
        """
        cmd = [
            "gallery-dl",
            "--dump-json",
            "--no-download",
            "--cookies", self.cookies_file,
            "--range", f"{start+1}-{start+count}",  # 1-indexed
            collection_url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            # Read JSON lines from stdout
            async for line in process.stdout:
                if line.strip():
                    try:
                        post_data = json.loads(line)
                        yield post_data
                    except json.JSONDecodeError:
                        continue

            await asyncio.wait_for(process.wait(), timeout=self.timeout)

        except asyncio.TimeoutError:
            process.kill()
            raise Exception("gallery-dl timeout")

    async def download_post(
        self,
        post_url: str,
        output_dir: str
    ) -> list[str]:
        """
        Download media for a single post
        Returns list of downloaded file paths
        """
        cmd = [
            "gallery-dl",
            "--cookies", self.cookies_file,
            "--dest", output_dir,
            post_url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=self.timeout
        )

        if process.returncode != 0:
            raise Exception(f"gallery-dl failed: {stderr.decode()}")

        # Parse output to find downloaded files
        # (Implementation depends on gallery-dl output format)
        downloaded_files = self._parse_downloaded_files(stdout.decode())
        return downloaded_files

    def _parse_downloaded_files(self, output: str) -> list[str]:
        """Extract file paths from gallery-dl output"""
        # Gallery-dl outputs lines like: "# /path/to/file.jpg"
        files = []
        for line in output.split('\n'):
            if line.startswith('# '):
                files.append(line[2:].strip())
        return files
```

### Cookie Export Instructions for Users

**Browser Extension Method** (Recommended):
1. Install "cookies.txt" or "Get cookies.txt" extension for Chrome/Firefox
2. Log into Instagram in your browser
3. Navigate to instagram.com
4. Click the extension icon → "Export" or "Get cookies.txt"
5. Save the file (it will look like `instagram.com_cookies.txt`)
6. Upload this file to SampleTok

**Manual Method** (Advanced):
1. Log into Instagram
2. Open DevTools (F12)
3. Go to Application → Cookies → https://instagram.com
4. Copy the values of: `sessionid`, `csrftoken`, `ds_user_id`
5. Format as: `sessionid=VALUE1; csrftoken=VALUE2; ds_user_id=VALUE3`
6. Paste into SampleTok cookie upload form

**Cookie Format**:
```
# Netscape HTTP Cookie File
.instagram.com	TRUE	/	TRUE	1767139200	sessionid	XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
.instagram.com	TRUE	/	TRUE	1735603200	csrftoken	XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
.instagram.com	TRUE	/	TRUE	1735603200	ds_user_id	12345678
```

---

## Database Migration Strategy

### Step 1: Add Platform Support (Backwards Compatible)
```python
# alembic/versions/xxx_add_platform_to_collections.py

def upgrade():
    # Add platform enum
    platform_enum = postgresql.ENUM('tiktok', 'instagram', name='platform_type')
    platform_enum.create(op.get_bind())

    # Add platform column with default 'tiktok' (all existing = TikTok)
    op.add_column('collections',
        sa.Column('platform', sa.Enum('tiktok', 'instagram', name='platform_type'),
                  nullable=False, server_default='tiktok'))

    # Add new generic columns (nullable for now)
    op.add_column('collections',
        sa.Column('platform_collection_id', sa.String(), nullable=True))
    op.add_column('collections',
        sa.Column('platform_username', sa.String(), nullable=True))

    # Copy data from TikTok-specific columns
    op.execute("""
        UPDATE collections
        SET platform_collection_id = tiktok_collection_id,
            platform_username = tiktok_username
    """)

    # Make new columns non-nullable
    op.alter_column('collections', 'platform_collection_id', nullable=False)
    op.alter_column('collections', 'platform_username', nullable=False)

    # Add indexes
    op.create_index('ix_collections_platform_collection_id',
                    'collections', ['platform_collection_id'])
    op.create_index('ix_collections_platform_username',
                    'collections', ['platform_username'])
    op.create_index('ix_collections_platform_user',
                    'collections', ['platform', 'platform_username', 'platform_collection_id'])

def downgrade():
    # Drop new columns and indexes
    op.drop_index('ix_collections_platform_user')
    op.drop_index('ix_collections_platform_username')
    op.drop_index('ix_collections_platform_collection_id')
    op.drop_column('collections', 'platform_username')
    op.drop_column('collections', 'platform_collection_id')
    op.drop_column('collections', 'platform')

    # Drop enum
    sa.Enum(name='platform_type').drop(op.get_bind())
```

### Step 2: Add Instagram Cookie Storage to Users
```python
# alembic/versions/yyy_add_instagram_cookies_to_users.py

def upgrade():
    op.add_column('users',
        sa.Column('instagram_cookies_encrypted', sa.Text(), nullable=True))
    op.add_column('users',
        sa.Column('instagram_cookies_updated_at', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('users', 'instagram_cookies_updated_at')
    op.drop_column('users', 'instagram_cookies_encrypted')
```

### Step 3: Deprecate TikTok-Specific Columns (Future)
After Instagram launch and stability:
```python
# alembic/versions/zzz_remove_tiktok_specific_columns.py

def upgrade():
    # Drop old TikTok-specific columns (data already migrated)
    op.drop_column('collections', 'tiktok_collection_id')
    op.drop_column('collections', 'tiktok_username')

def downgrade():
    # Restore for rollback
    op.add_column('collections', sa.Column('tiktok_collection_id', sa.String()))
    op.add_column('collections', sa.Column('tiktok_username', sa.String()))

    # Copy back from platform columns where platform='tiktok'
    op.execute("""
        UPDATE collections
        SET tiktok_collection_id = platform_collection_id,
            tiktok_username = platform_username
        WHERE platform = 'tiktok'
    """)
```

---

## Error Handling Matrix

| Error Type | Cause | Handling Strategy | User Impact |
|------------|-------|-------------------|-------------|
| **Invalid URL** | Malformed Instagram URL | Validate format before submission | Immediate error, no credits charged |
| **Invalid Cookies** | Expired/wrong cookies | Validate before processing starts | Immediate error, no credits charged |
| **Auth Failure Mid-Process** | Cookies expired during import | Pause collection, notify user, allow resume | Credits held, can resume after re-auth |
| **Rate Limited (429)** | Too many requests to Instagram | Exponential backoff, retry | Automatic retry, transparent to user |
| **Post Deleted/Private** | Post no longer accessible | Skip post, refund 1 credit | Refund, continue with remaining posts |
| **gallery-dl Crash** | Unexpected subprocess failure | Retry 3x, then mark post as failed | Refund for failed post, continue batch |
| **Network Timeout** | Slow connection during download | Retry with increased timeout | Automatic retry, transparent to user |
| **Storage Upload Failure** | S3/R2/GCS error | Retry upload 3x, then fail post | Refund for failed post |
| **Audio Extraction Failure** | Corrupted video file | Skip audio analysis, store video only | No refund (video downloaded successfully) |
| **Out of Credits Mid-Batch** | User canceled subscription | Pause processing, refund unprocessed | Processing stops gracefully |

---

## Monitoring & Observability

### Metrics to Track
1. **Processing Success Rate**: `successful_posts / total_posts` per collection
2. **Average Processing Time**: Time from submission to completion
3. **Cookie Expiration Rate**: How often auth fails mid-process
4. **Rate Limit Hit Rate**: Frequency of 429 errors
5. **gallery-dl Failure Rate**: Subprocess crashes or timeouts
6. **Credit Refund Rate**: Percentage of posts that fail and refund

### Logging Strategy
```python
# In InstagramCollectionService
logger.info(
    "instagram_collection_started",
    extra={
        "collection_id": collection.id,
        "platform_collection_id": collection.platform_collection_id,
        "user_id": collection.user_id,
        "total_posts": collection.total_video_count
    }
)

logger.error(
    "instagram_post_failed",
    extra={
        "collection_id": collection.id,
        "post_url": post_url,
        "error": str(e),
        "will_refund": True
    }
)
```

### Alerts to Configure
1. **High Failure Rate**: >20% of posts failing in a collection
2. **Cookie Expiration Spike**: >10 auth failures per hour
3. **Rate Limit Threshold**: >5 rate limit errors per minute
4. **gallery-dl Unavailable**: Subprocess failures >50%

---

## Testing Strategy

### Unit Tests
```python
# tests/test_instagram_collection_service.py
async def test_fetch_collection_metadata():
    service = InstagramCollectionService(cookies_file="test_cookies.txt")
    metadata = await service.fetch_collection_metadata(
        "https://www.instagram.com/user/saved/test/12345/"
    )
    assert metadata["collection_id"] == "12345"
    assert metadata["collection_name"] == "test"

# tests/test_gallery_dl_wrapper.py
async def test_download_post_success():
    wrapper = GalleryDLWrapper(cookies_file="test_cookies.txt")
    files = await wrapper.download_post(
        "https://www.instagram.com/p/ABC123/",
        "/tmp/test"
    )
    assert len(files) > 0
```

### Integration Tests
```python
# tests/integration/test_instagram_collection_flow.py
async def test_full_collection_import():
    """Test end-to-end Instagram collection import"""
    # 1. Upload cookies
    # 2. Submit collection URL
    # 3. Wait for processing
    # 4. Verify all posts downloaded
    # 5. Verify credits deducted correctly
    # 6. Verify samples created in database
```

### Manual Test Cases
1. **Happy Path**: Import small collection (5 posts) successfully
2. **Large Collection**: Import 100+ post collection with batching
3. **Mixed Media**: Collection with videos and images
4. **Partial Failures**: Collection with some deleted/private posts
5. **Cookie Expiration**: Mid-process auth failure and resume
6. **Rate Limiting**: Trigger rate limit and verify backoff
7. **Duplicate Detection**: Re-import same collection (should skip existing)
8. **Credit Refunds**: Verify refunds for failed posts

---

## Security Considerations

### Cookie Storage Security
1. **Encryption at Rest**: Use Fernet (AES-128) for cookie encryption
2. **Key Management**: Store encryption key in GCP Secret Manager
3. **Key Rotation**: Implement periodic key rotation (every 90 days)
4. **Access Control**: Only backend services can decrypt cookies
5. **Audit Trail**: Log cookie uploads/updates (not values)

### Cookie Transmission Security
1. **HTTPS Only**: All API endpoints require HTTPS
2. **No Logging**: Never log cookie values in plain text
3. **No Cache**: Set `Cache-Control: no-store` on cookie endpoints
4. **CORS Restrictions**: Strict CORS policy for cookie upload

### Instagram ToS Compliance
1. **User-Owned Content**: Only process user's own saved collections
2. **Rate Limiting**: Respect Instagram's rate limits strictly
3. **No Bulk Scraping**: Prevent abuse for mass data collection
4. **User Control**: Allow users to delete cookies/data anytime
5. **Transparency**: Clear user agreement about automation

---

## Deployment Checklist

### Pre-Deployment
- [ ] Install gallery-dl in Docker image (`pip install gallery-dl`)
- [ ] Add `INSTAGRAM_COOKIES_ENCRYPTION_KEY` to Secret Manager
- [ ] Test gallery-dl with real Instagram account
- [ ] Verify cookie encryption/decryption works
- [ ] Run database migrations in staging
- [ ] Load test with 10 concurrent collection imports

### Deployment
- [ ] Deploy backend with new endpoints
- [ ] Run migrations in production
- [ ] Deploy frontend with Instagram UI
- [ ] Verify Inngest function registered
- [ ] Test end-to-end with real user cookies
- [ ] Monitor error rates for first 24 hours

### Post-Deployment
- [ ] Create user documentation for cookie export
- [ ] Set up monitoring alerts
- [ ] Announce feature to users
- [ ] Collect user feedback
- [ ] Monitor rate limit errors
- [ ] Track cookie expiration patterns

---

## Future Enhancements

### Phase 2 Features (Post-Launch)
1. **Automatic Cookie Refresh**: Integrate with Instagram login API
2. **Multi-Account Support**: Import from multiple Instagram accounts
3. **Smart Filtering**: Filter by media type, date range, hashtags
4. **Scheduled Imports**: Auto-sync collections daily/weekly
5. **Collection Merging**: Combine multiple Instagram collections
6. **Export to Spotify**: Generate playlists from audio samples

### Additional Platforms
Once Instagram is stable, apply the same pattern to:
- **YouTube Playlists**: Similar collection concept
- **SoundCloud Likes**: User-saved audio tracks
- **Twitter Bookmarks**: Saved tweets with media
- **Pinterest Boards**: User-curated collections

---

## Questions & Decisions Needed

### Before Implementation Starts
1. **Cookie Storage**: Store per-user or per-collection? (Recommendation: per-user)
2. **Image-Only Posts**: Should we process or skip? (Recommendation: skip, audio-focused app)
3. **Credit Pricing**: Same as TikTok (1 credit/post) or different? (Recommendation: same)
4. **Rate Limit**: How conservative should we be? (Recommendation: 30 req/min)
5. **Max Collection Size**: Should we limit? (Recommendation: 500 posts initially)

### Technical Decisions
1. **gallery-dl vs Instaloader**: Which library? (Recommendation: gallery-dl)
2. **Subprocess vs Library**: Wrap CLI or use Python library? (Recommendation: subprocess for stability)
3. **Cookie Format**: Netscape format or JSON? (Recommendation: Netscape for gallery-dl compatibility)
4. **Error Retry Strategy**: How many retries per post? (Recommendation: 3 retries with exponential backoff)

---

## Success Metrics (3 Months Post-Launch)

**Adoption Metrics**:
- [ ] 30% of active users import at least one Instagram collection
- [ ] Average 50 Instagram collections imported per week
- [ ] 80% collection completion rate (no failures)

**Technical Metrics**:
- [ ] <5% post failure rate
- [ ] <1% cookie expiration rate mid-process
- [ ] <10 rate limit errors per day
- [ ] Average processing time: <30 seconds per post

**User Satisfaction**:
- [ ] >4.5/5 user rating for Instagram import feature
- [ ] <5% support tickets related to Instagram imports
- [ ] >80% users successfully export cookies on first try

---

This plan provides a comprehensive roadmap for implementing Instagram collection support with full feature parity to the existing TikTok system. The architecture is proven, the risks are mitigated, and the implementation is phased for manageable delivery.
