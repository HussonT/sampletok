# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Important: Backend Hot Reload

The backend has hot reload enabled. **DO NOT** start and restart the backend
unnecessarily - it will automatically reload on code changes.

## Development Commands

### Backend (FastAPI)

```bash
cd backend

# Initial setup
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start infrastructure (PostgreSQL + MinIO)
docker-compose up -d

# Database migrations
alembic upgrade head                              # Apply all migrations
alembic revision --autogenerate -m "description"  # Create new migration
alembic downgrade -1                              # Rollback one migration

# Run backend (with hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access OpenAPI docs
# http://localhost:8000/api/v1/docs
```

### Frontend (Next.js)

**Requires Node.js >=22.0.0**

```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build
npm start

# Linting
npm run lint
```

## Architecture Overview

### Backend Structure

**FastAPI + Inngest Background Workers**

- `app/main.py` - FastAPI application entry point, CORS, Inngest endpoint at
  `/api/inngest`
- `app/core/` - Configuration, database connection
- `app/models/` - SQLAlchemy models (Sample, User, TikTokCreator)
- `app/api/v1/` - REST API endpoints (samples, process, test)
- `app/services/` - Business logic:
  - `audio/` - Audio extraction, waveform generation, BPM/key analysis
  - `storage/` - S3/MinIO/R2/GCS upload/download
  - `tiktok/` - TikTok video download via RapidAPI, creator service
- `app/inngest_functions.py` - Async background jobs for video processing
  pipeline
- `alembic/` - Database migrations

### Processing Pipeline (Inngest)

When a TikTok URL is submitted, Inngest orchestrates an 8-step pipeline:

1. **Update status** - Mark sample as "processing"
2. **Download video** - Fetch from TikTok via RapidAPI, extract metadata,
   fetch/cache creator info
3. **Extract audio** - Convert to WAV + MP3, get duration/sample rate
4. **Generate waveform** - Create PNG visualization
5. **Analyze audio** - Detect BPM and musical key using librosa/essentia
6. **Upload files** - Store WAV, MP3, waveform in S3/MinIO/R2/GCS
7. **Update database** - Save all metadata, URLs, analysis results, link to
   TikTok creator
8. **Cleanup** - Remove temporary files

All steps are retried automatically on failure. If the entire pipeline fails, a
separate error handler marks the sample as failed.

### Database Models

**Sample** (`app/models/sample.py`)

- Stores TikTok metadata (creator, views, likes, description)
- Audio metadata (duration, BPM, key)
- File URLs (WAV, MP3, waveform, thumbnails)
- Processing status (pending/processing/completed/failed)
- Relationships: creator (User), tiktok_creator (TikTokCreator), downloaded_by
  (many-to-many with User)

**TikTokCreator** (`app/models/tiktok_creator.py`)

- Cached creator info (username, display name, follower count, avatar)
- Smart caching: only re-fetches if data is >7 days old
- Linked to samples via `tiktok_creator_id`

**User** - Authentication, sample ownership, download tracking

### Storage Architecture

**S3Storage** (`app/services/storage/s3.py`) supports:

- **AWS S3** - Standard S3 buckets
- **MinIO** - Local development (via docker-compose)
- **Cloudflare R2** - S3-compatible, no egress fees
- **Google Cloud Storage (GCS)** - For GCP deployments

Configuration via `STORAGE_TYPE` env var. Handles upload, download, delete,
public URL generation.

### Audio Playback Performance Optimizations

The application implements several optimizations for instant audio playback:

**Backend Optimizations:**

- **Aggressive Caching**: All audio files (MP3/WAV) and waveforms uploaded with
  `Cache-Control: public, max-age=31536000, immutable` headers
- **HTTP Range Request Support**: Audio files support byte-range requests for
  progressive download
- **Direct URL Access**: Frontend uses direct storage URLs for playback (not
  proxied through backend)

**Frontend Optimizations:**

- **Smart Preloading Strategy**:
  - Audio elements use `preload="metadata"` to load only headers until play is
    clicked
  - High-priority preload of next/previous tracks when a sample is playing
  - Hover-to-preload: Audio starts downloading when user hovers over play button
  - Removed aggressive prefetching (previously loaded all 20 samples = ~24MB)
- **HTTP Range Requests**: Browser automatically uses Range requests to load
  first chunk for instant playback
- **CORS Support**: Audio elements include `crossOrigin="anonymous"` for proper
  caching

**HLS Streaming (Tier 2 - Professional Grade):**

- **Adaptive Streaming**: Audio segmented into 2-second chunks (AAC 320kbps)
- **Instant Playback**: Loads first segment (~80KB) instead of full file (1.2MB)
- **Smart Buffering**: hls.js manages buffer (10s back, 30s ahead, 60s max)
- **Seamless Fallback**: Auto-falls back to MP3 if HLS unavailable or
  unsupported
- **Browser Support**:
  - Modern browsers: HLS via hls.js (Chrome, Firefox, Edge)
  - Safari: Native HLS support
  - Fallback: Direct MP3 playback

**Performance Results:**

- First play: <200ms (down from ~2s) - HLS streaming
- Repeat plays: <50ms (browser cache)
- Page load bandwidth: ~500KB (down from ~24MB)
- Hover-to-play: Instant (<100ms perceived latency)
- Seek performance: Instant (no need to download full file)

**CDN Setup (Recommended for Production):**

For Cloudflare R2:

1. Enable R2 custom domain or R2.dev subdomain in Cloudflare dashboard
2. Set `R2_PUBLIC_DOMAIN` environment variable to your domain
3. Cloudflare automatically caches files with `Cache-Control` headers
4. No additional CDN configuration needed - R2 includes global CDN

For AWS S3:

1. Create CloudFront distribution pointing to S3 bucket
2. Configure CloudFront to respect `Cache-Control` headers
3. Update `get_public_url()` in `app/services/storage/s3.py` to return
   CloudFront URLs
4. Set CloudFront cache behaviors for `*.mp3`, `*.wav`, `*.png` file types

For GCS:

1. Enable Cloud CDN on the GCS bucket
2. Configure cache settings to respect `Cache-Control` headers
3. Files will be automatically cached at Google edge locations

**Implementation Details:**

- **Backend:**
  - Cache headers: `app/services/storage/s3.py:_upload_to_s3()`
  - HLS generation: `app/services/audio/processor.py:generate_hls_stream()`
  - Inngest pipeline: `app/inngest_functions.py:generate_hls_stream()`
  - Database model: `app/models/sample.py` (audio_url_hls field)
  - Backfill script: `scripts/backfill_hls_streams.py` (for existing samples)
- **Frontend:**
  - HLS player wrapper: `frontend/app/components/features/hls-audio-player.tsx`
  - Preload strategy: `frontend/app/components/main-app.tsx`
  - Hover handlers: `frontend/app/components/features/sounds-table.tsx`
  - Player integration: `frontend/app/components/features/bottom-player.tsx` &
    `audio-player.tsx`

**Backfilling HLS for Existing Samples:**

New samples will automatically get HLS streams during processing. For existing
samples, use the backfill script:

```bash
cd backend

# Preview what will be processed
python scripts/backfill_hls_streams.py --dry-run

# Process all samples without HLS
python scripts/backfill_hls_streams.py

# Process only first 10 (for testing)
python scripts/backfill_hls_streams.py --limit 10
```

See `backend/scripts/README.md` for detailed usage and options.

### Frontend Structure

**Next.js 15 with App Router + React 19**

Key technologies:

- **Authentication**: Clerk (@clerk/nextjs)
- **State Management**: TanStack Query (@tanstack/react-query)
- **UI Components**: Radix UI primitives + shadcn/ui patterns
- **Styling**: Tailwind CSS with animations
- **Icons**: Lucide React
- **Theme**: next-themes for dark mode

Directory structure:

- `frontend/app/(routes)/` - Page routes
- `frontend/app/components/` - React components
- `frontend/app/api/` - API route handlers (server-side)
- `frontend/app/actions/` - Server actions
- `frontend/app/lib/` - Utilities, API client
- `frontend/app/types/` - TypeScript type definitions

## Configuration

### Environment Variables

Backend requires:

- `DATABASE_URL` - PostgreSQL connection string (asyncpg format)
- `RAPIDAPI_KEY` - TikTok API access (required)
- `LALAL_API_KEY` - La La AI API key for stem separation (optional, required for
  stem features)
- `SECRET_KEY`, `JWT_SECRET_KEY` - Auth secrets
- `INNGEST_EVENT_KEY`, `INNGEST_SIGNING_KEY` - Background job service
- Storage config: `STORAGE_TYPE`, AWS/R2/GCS credentials
- CORS: `BACKEND_CORS_ORIGINS` - Frontend URLs (JSON array string)
- Rate limiting: `STEM_SEPARATION_RATE_LIMIT_PER_MINUTE`,
  `STEM_DOWNLOAD_RATE_LIMIT_PER_MINUTE`
- Stem limits: `MAX_STEMS_PER_REQUEST`, `MAX_CONCURRENT_DOWNLOADS_PER_USER`

Frontend requires:

- `NEXT_PUBLIC_API_URL` - Backend API URL

See `backend/.env.example` for full reference.

### Local Development Setup

1. Copy `backend/.env.example` to `backend/.env`
2. Start Docker services: `cd backend && docker-compose up -d`
3. Run migrations: `cd backend && alembic upgrade head`
4. Start backend: `cd backend && uvicorn app.main:app --reload`
5. Create `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
6. Start frontend: `cd frontend && npm run dev`

MinIO console: http://localhost:9001 (minioadmin/minioadmin)

## Key Technical Details

### Audio Processing

- Uses `ffmpeg` for extraction (48kHz, 24-bit WAV + 320kbps MP3)
- `librosa` for BPM detection (tempo estimation)
- `essentia` for musical key detection (via Essentia's KeyExtractor)
- Waveform generated as PNG using numpy/PIL

### TikTok Integration

Uses RapidAPI's "TikTok Video No Watermark" service. Returns:

- Video metadata (views, likes, comments, shares)
- Creator info (username, display name, avatar)
- No-watermark video URL
- Original audio URL
- Thumbnails and cover images

### Instagram Integration

**Two-part integration for Instagram support:**

**Part 1: Video Processing** (via RapidAPI)
- Uses RapidAPI's "Instagram Best Experience" service for video downloads
- Similar to TikTok processing: download video, extract audio, analyze, upload
- Creator info cached in `instagram_creators` table with smart caching (<7 days TTL)

**Part 2: Auto-Engagement** (via Instagram Graph API)
- **Service**: `InstagramGraphAPIClient` (`app/services/instagram/graph_api.py`)
- **Database**: `instagram_engagements` table tracks mentions, comments, and processing status
- **Webhooks**: Receives mention notifications at `/api/v1/webhooks/instagram`

**Architecture Flow:**
1. User tags `@sampletheinternet` in Instagram post
2. Instagram Graph API sends webhook to our backend
3. Webhook creates `InstagramEngagement` record (status: PENDING)
4. Inngest job triggered to process video and extract audio (future: TPERS-473)
5. Sample created and auto-comment posted with sample link (status: COMPLETED)

**Required Credentials** (see `backend/docs/INSTAGRAM_GRAPH_API_SETUP.md` for full setup):
- `INSTAGRAM_APP_ID` - Facebook App ID
- `INSTAGRAM_APP_SECRET` - Facebook App Secret
- `INSTAGRAM_ACCESS_TOKEN` - Long-lived access token (60-day expiry, must refresh)
- `INSTAGRAM_BUSINESS_ACCOUNT_ID` - Instagram Business Account ID
- `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` - Random token for webhook verification

**Key Features:**
- Get media info and metadata from Graph API
- Post comments on Instagram media
- Receive mention notifications via webhooks
- Webhook verification for security
- Token refresh mechanism (60-day expiry)
- Error handling for expired tokens, disabled comments, rate limits

**Rate Limits:**
- Development Mode: 200 calls/hour per user, 25 test users max
- Production Mode (verified business): 4,800 calls/hour per user, unlimited users

**Security:**
- Webhook signature verification (verify token)
- Long-lived tokens stored securely (environment variables)
- Separate credentials for dev/staging/production
- Token refresh strategy (monthly cron job)

**Testing:**
- Health check: `GET /api/v1/webhooks/instagram/health`
- Manual comment test: `InstagramGraphAPIClient().post_comment()`
- Webhook test: Tag `@sampletheinternet` in test post

**Documentation:**
- Full setup guide: `backend/docs/INSTAGRAM_GRAPH_API_SETUP.md`
- API reference: https://developers.facebook.com/docs/instagram-api

### Stem Separation (La La AI Integration)

**Service:** `LalalAIService` (`app/services/audio/lalal_service.py`)

Enables users to separate audio samples into individual instrument/vocal stems
using La La AI's API.

**Supported Stem Types (Phoenix Model):**

- `vocal` - Main vocals
- `voice` - Voice/speech
- `drum` - Drums and percussion
- `piano` - Piano
- `bass` - Bass guitar/synth bass
- `electric_guitar` - Electric guitar
- `acoustic_guitar` - Acoustic guitar
- `synthesizer` - Synthesizers
- `strings` - String instruments
- `wind` - Wind instruments

**Architecture:**

- User submits stem separation request via `POST /samples/{id}/separate-stems`
- Credits deducted upfront (2 credits per stem)
- Inngest job triggered for async processing
- Original audio uploaded to La La AI
- Separation task submitted with stem types
- Polling (every 5 seconds) until completion or timeout (10 minutes)
- Separated stems downloaded and analyzed (BPM, key, duration)
- Files uploaded to storage (WAV + MP3)
- Database updated with stem metadata
- **Error handling:** Failed jobs automatically refund credits to users

**Processing Flow:**

1. Upload original audio to La La AI (max 10GB file size)
2. Submit separation task with stem parameters
3. Poll for completion (task.state: `pending` → `progress` → `success`)
4. Download separated audio files
5. Analyze each stem (BPM, key detection)
6. Upload to storage (S3/R2/GCS)
7. Update database with URLs and metadata

**Rate Limiting & Limits:**

- Submission: 5 requests/minute per user
- Downloads: 30 requests/minute per user
- Max stems per request: 5
- Max concurrent downloads per user: 3
- File size limit: 10GB (La La AI constraint)

**Credit System:**

- 2 credits per stem for separation
- 1 credit for first download (WAV or MP3)
- Re-downloads are free
- Credits automatically refunded if separation fails

**API Keys & Setup:**

- Requires `LALAL_API_KEY` environment variable
- Sign up at https://www.lalal.ai/api/
- Choose plan based on usage (rate limits and quotas vary)
- Monitor quota usage via La La AI dashboard

**Error Handling:**

- Custom exception hierarchy: `LalalAIException` (base)
  - `LalalAPIKeyError` - Invalid/missing API key (401/403)
  - `LalalRateLimitError` - Rate limit exceeded (429)
  - `LalalQuotaExceededError` - Quota exhausted (402)
  - `LalalFileError` - File too large/invalid (413)
  - `LalalProcessingError` - Separation failed (400)
  - `LalalTimeoutError` - Polling timeout (10 min)

**Troubleshooting:**

- **"LALAL_API_KEY environment variable is required"**: Set API key in `.env`
  file
- **"Quota exceeded"**: Upgrade La La AI plan or wait for quota reset
- **"File too large"**: Sample exceeds 10GB limit (rare for TikTok videos)
- **Polling timeout**: Job took >10 minutes (increase `max_wait_seconds` if
  needed)
- **Rate limit errors**: Reduce concurrent requests or wait for rate limit reset

### Rate Limiting

Backend uses `slowapi` for rate limiting on specific endpoints:

- Collections endpoint has rate limits to prevent abuse
- Rate limiting is IP-based by default
- Configure limits per endpoint in the route decorator

### Creator Service Caching

`CreatorService.get_or_fetch_creator()` intelligently:

- Checks if creator exists in DB
- If exists and fresh (<7 days), returns cached data
- If stale, re-fetches from API and updates
- If doesn't exist, fetches and creates new record

Prevents redundant API calls when processing multiple videos from same creator.

### Database Migrations

Uses Alembic with async support. Models are in `app/models/`, migrations in
`alembic/versions/`.

When adding/modifying models:

1. Update SQLAlchemy model in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. **Review generated migration carefully** - delete checklist, verify
   schema-only
4. **Run validation:** `python backend/scripts/check_migrations.py`
5. Test locally: `alembic upgrade head && alembic downgrade -1`
6. Commit migration file

**CRITICAL:** See `backend/alembic/MIGRATION_GUIDELINES.md` before creating
migrations!

### Migrations vs SQL Scripts

**IMPORTANT:** Alembic migrations should ONLY contain schema changes. Never put
business logic or one-time data operations in migrations.

**Use Alembic Migrations For:**

- Schema changes (tables, columns, indexes, constraints)
- Structural modifications that must be applied to all environments
- Changes that new databases need during initial setup

Examples:

```bash
alembic revision -m "Add subscription table"
alembic revision -m "Add index on user_email"
alembic revision -m "Add NOT NULL constraint to tier column"
```

**Use SQL Scripts (`backend/scripts/sql/`) For:**

- One-time data operations for production
- Bulk data updates or cleanup
- Business logic changes that don't affect schema
- Operations that should be reviewed before running

Examples:

- Resetting user credits for a launch
- Bulk updating legacy data
- Data migration between systems
- Cleanup of test/duplicate data

**Running SQL Scripts:**

```bash
# Always review first
cat backend/scripts/sql/script-name.sql

# Create backup
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d-%H%M%S).sql

# Run the script
psql $DATABASE_URL -f backend/scripts/sql/script-name.sql
```

See `backend/scripts/README.md` for detailed guidelines on when to use
migrations vs scripts.

## API Endpoints

**Key endpoints** (`/api/v1/`):

- `POST /process/submit` - Submit TikTok URL for processing (triggers Inngest
  job)
- `GET /samples` - List samples (with pagination, filtering, search)
- `GET /samples/{id}` - Get sample details
- `POST /samples/{id}/download` - Download sample MP3 (increments download
  count)
- `GET /collections` - List sample collections/playlists (with rate limiting)
- `POST /collections/{id}/reset` - User-facing endpoint to reset stuck
  collections and refund credits
- `GET /test/inngest` - Test Inngest integration

**Admin endpoints** (`/api/v1/admin/`, requires `X-Admin-Key` header):

- `POST /admin/reset-user-collections?clerk_id={clerk_id}` - Reset all stuck
  collections for a user by Clerk ID
- `POST /admin/reset-collection/{collection_id}` - Reset a specific collection
  by ID and refund credits
- `POST /admin/add-credits` - Add credits to a user by Clerk ID (request body:
  `{"clerk_id": "user_xxx", "credits": 100}`)
- `POST /admin/backfill-hls` - Generate HLS streaming playlists for existing
  samples (request body: `{"limit": 10, "dry_run": false}`)

All admin endpoints require the `X-Admin-Key` header matching the `SECRET_KEY`
environment variable.

Full API docs: http://localhost:8000/api/v1/docs

## Testing

No formal test suite currently. Test via:

- OpenAPI docs: http://localhost:8000/api/v1/docs
- Inngest dev server: https://www.inngest.com/docs/local-development
- Manual frontend testing

## Inngest Production Setup

### Local Development (Default)

- Uses Inngest Dev Server (no keys needed)
- Leave `INNGEST_EVENT_KEY` and `INNGEST_SIGNING_KEY` blank in `.env`
- Run: `npx inngest-cli@latest dev` in a separate terminal
- Access dev UI: http://localhost:8288

### Production Configuration

1. **Create Inngest Account & App**
   - Sign up at https://app.inngest.com
   - Create a new app (e.g., "sampletok")
   - Navigate to your production environment

2. **Get Production Keys**
   - Go to: https://app.inngest.com/env/production/manage/keys
   - Copy your **Event Key** (starts with "inngest_event_key_...")
   - Copy your **Signing Key** (for webhook security)

3. **Configure Environment Variables**
   ```bash
   ENVIRONMENT=production
   INNGEST_EVENT_KEY=inngest_event_key_...
   INNGEST_SIGNING_KEY=signkey-prod-...
   ```

4. **Sync Functions to Inngest Cloud** After deploying your backend:
   ```bash
   # Option 1: Sync via Inngest Cloud UI
   # Navigate to your app → "Sync App" → Enter your backend URL
   # URL: https://your-backend.com/api/inngest

   # Option 2: Sync via curl
   curl -X PUT https://your-backend.com/api/inngest
   ```

5. **Verify Setup**
   - Functions should appear in Inngest Cloud UI
   - Test with: `POST /api/v1/test/inngest` endpoint
   - Check Inngest Cloud for function execution logs

### Important Notes

- Backend must be publicly accessible for Inngest Cloud to reach it
- `/api/inngest` endpoint handles both function sync and webhook events
- Re-sync after deploying new functions or changes
- Monitor function execution in Inngest Cloud dashboard

## Deployment

See `DEPLOYMENT.md` for detailed deployment guides:

- **Recommended**: Vercel (frontend) + GCP Cloud Run (backend)
- Alternatives: Railway, DigitalOcean VPS, Docker Compose

### Quick GCP Deployment

**Manual deployment** via `deploy.sh`:

```bash
cd backend
./deploy.sh [tag]  # Builds, pushes to Artifact Registry, and deploys to Cloud Run
```

**Automatic deployment** via GitHub Actions:

- `.github/workflows/deploy-backend.yml` automatically deploys backend to Cloud
  Run on push to `main` branch (when backend files change)
- Requires `GCP_SA_KEY` secret in GitHub repo
- Includes health check verification after deployment

### Deployment Checklist

Key deployment considerations:

- Backend migrations run automatically in Dockerfile startup script (`runit.sh`)
- Use GCP Secret Manager for production secrets (DATABASE_URL, API keys, etc.)
- Configure CORS with production frontend URLs via `BACKEND_CORS_ORIGINS` secret
- Set up Inngest webhook to backend `/api/inngest` endpoint (see Inngest
  Production Setup above)
- Choose storage backend (AWS S3, Cloudflare R2, or GCS) via `STORAGE_TYPE` env
  var
- Cloud Run configured with: 2Gi memory, 2 CPU, 0-10 instances, 300s timeout
- Backend connects to Cloud SQL PostgreSQL via Unix socket
- No backwards compatibility or fallbacks in future implementations. Just
  implement the new solution cleanly and move forward.
