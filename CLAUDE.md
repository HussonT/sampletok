# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important: Backend Hot Reload

The backend has hot reload enabled. **DO NOT** start and restart the backend unnecessarily - it will automatically reload on code changes.

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

```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build
npm start
```

## Architecture Overview

### Backend Structure

**FastAPI + Inngest Background Workers**

- `app/main.py` - FastAPI application entry point, CORS, Inngest endpoint at `/api/inngest`
- `app/core/` - Configuration, database connection
- `app/models/` - SQLAlchemy models (Sample, User, TikTokCreator)
- `app/api/v1/` - REST API endpoints (samples, process, test)
- `app/services/` - Business logic:
  - `audio/` - Audio extraction, waveform generation, BPM/key analysis
  - `storage/` - S3/MinIO/R2/GCS upload/download
  - `tiktok/` - TikTok video download via RapidAPI, creator service
- `app/inngest_functions.py` - Async background jobs for video processing pipeline
- `alembic/` - Database migrations

### Processing Pipeline (Inngest)

When a TikTok URL is submitted, Inngest orchestrates an 8-step pipeline:

1. **Update status** - Mark sample as "processing"
2. **Download video** - Fetch from TikTok via RapidAPI, extract metadata, fetch/cache creator info
3. **Extract audio** - Convert to WAV + MP3, get duration/sample rate
4. **Generate waveform** - Create PNG visualization
5. **Analyze audio** - Detect BPM and musical key using librosa/essentia
6. **Upload files** - Store WAV, MP3, waveform in S3/MinIO/R2/GCS
7. **Update database** - Save all metadata, URLs, analysis results, link to TikTok creator
8. **Cleanup** - Remove temporary files

All steps are retried automatically on failure. If the entire pipeline fails, a separate error handler marks the sample as failed.

### Database Models

**Sample** (`app/models/sample.py`)
- Stores TikTok metadata (creator, views, likes, description)
- Audio metadata (duration, BPM, key)
- File URLs (WAV, MP3, waveform, thumbnails)
- Processing status (pending/processing/completed/failed)
- Relationships: creator (User), tiktok_creator (TikTokCreator), downloaded_by (many-to-many with User)

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

Configuration via `STORAGE_TYPE` env var. Handles upload, download, delete, public URL generation.

### Frontend Structure

**Next.js 15 with App Router**

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
- `SECRET_KEY`, `JWT_SECRET_KEY` - Auth secrets
- `INNGEST_EVENT_KEY`, `INNGEST_SIGNING_KEY` - Background job service
- Storage config: `STORAGE_TYPE`, AWS/R2/GCS credentials
- CORS: `BACKEND_CORS_ORIGINS` - Frontend URLs (JSON array string)

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

### Creator Service Caching

`CreatorService.get_or_fetch_creator()` intelligently:
- Checks if creator exists in DB
- If exists and fresh (<7 days), returns cached data
- If stale, re-fetches from API and updates
- If doesn't exist, fetches and creates new record

Prevents redundant API calls when processing multiple videos from same creator.

### Database Migrations

Uses Alembic with async support. Models are in `app/models/`, migrations in `alembic/versions/`.

When adding/modifying models:
1. Update SQLAlchemy model in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration file (may need manual edits)
4. Test locally: `alembic upgrade head`
5. Commit migration file

## API Endpoints

**Key endpoints** (`/api/v1/`):
- `POST /process/submit` - Submit TikTok URL for processing (triggers Inngest job)
- `GET /samples` - List samples (with pagination, filtering, search)
- `GET /samples/{id}` - Get sample details
- `POST /samples/{id}/download` - Download sample MP3 (increments download count)
- `GET /test/inngest` - Test Inngest integration

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

4. **Sync Functions to Inngest Cloud**
   After deploying your backend:
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

Key deployment considerations:
- Backend migrations run automatically in Dockerfile startup script
- Use Secret Manager (GCP) or environment variables for secrets
- Configure CORS with production frontend URLs
- Set up Inngest webhook to backend `/api/inngest` endpoint (see Inngest Production Setup above)
- Choose storage backend (AWS S3, Cloudflare R2, or GCS)
