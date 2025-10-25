# Backend Scripts

## Remote API Trigger (RECOMMENDED)

You can now trigger reprocessing remotely via the FastAPI endpoint:

### Endpoint

```
POST /api/v1/samples/reprocess
```

### Request Body

```json
{
  "filter_status": "completed",  // Optional: pending, processing, completed, failed
  "limit": 10,                   // Optional: max number to process
  "skip_reset": false,           // Optional: don't reset status to pending
  "dry_run": true,              // Optional: preview without processing
  "broken_links_only": true     // Optional: only reprocess samples with broken/missing URLs
}
```

### Examples

```bash
# Dry run - see what would be processed
curl -X POST http://localhost:8000/api/v1/samples/reprocess \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true, "limit": 5}'

# Reprocess all samples
curl -X POST http://localhost:8000/api/v1/samples/reprocess \
  -H "Content-Type: application/json" \
  -d '{}'

# Reprocess only failed samples
curl -X POST http://localhost:8000/api/v1/samples/reprocess \
  -H "Content-Type: application/json" \
  -d '{"filter_status": "failed"}'

# Reprocess first 10 samples
curl -X POST http://localhost:8000/api/v1/samples/reprocess \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'

# Reprocess ONLY samples with broken/missing URLs
curl -X POST http://localhost:8000/api/v1/samples/reprocess \
  -H "Content-Type: application/json" \
  -d '{"broken_links_only": true}'
```

### Response

```json
{
  "message": "Started reprocessing 10 samples in the background. Check logs for progress.",
  "total_samples": 10,
  "status": "started"
}
```

The processing runs in the background, so the API returns immediately. Monitor progress in the backend logs.

---

## 1. Reprocess All Samples (CLI Script)

### Purpose
**Completely reprocesses all existing samples through the full Inngest pipeline.** This is the most thorough option and ensures everything is downloaded fresh from TikTok and stored properly.

### When to Use
- ✅ **After upgrading to self-hosted media architecture** (this is you!)
- When you want to ensure all media is fresh and up-to-date
- When you want to re-analyze BPM/key for existing samples
- When you want to regenerate waveforms with updated algorithms

### What It Does

For each sample, the script triggers the **complete Inngest pipeline**:

1. **Download** - Fresh download of video from TikTok
2. **Upload Video** - Store video in `samples/{id}/video.mp4`
3. **Download Media** - Get thumbnails and covers from TikTok
4. **Upload Media** - Store in `samples/{id}/thumbnail.jpg` and `cover.jpg`
5. **Extract Audio** - Generate WAV + MP3 files
6. **Upload Audio** - Store in your infrastructure
7. **Generate Waveform** - Create PNG visualization
8. **Analyze Audio** - Detect BPM and musical key
9. **Fetch Creator** - Download and store creator avatars
10. **Update Database** - Save all metadata and URLs

### How to Run

```bash
# From the backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# DRY RUN FIRST - see what will be processed
python -m scripts.reprocess_all_samples --dry-run

# Reprocess ALL samples
python -m scripts.reprocess_all_samples

# Reprocess only failed samples
python -m scripts.reprocess_all_samples --status failed

# Reprocess only first 5 samples (for testing)
python -m scripts.reprocess_all_samples --limit 5
```

### Command Line Options

- `--dry-run` - Preview what will be processed without actually doing it
- `--status <status>` - Only reprocess samples with specific status (`pending`, `processing`, `completed`, `failed`)
- `--limit <number>` - Limit to first N samples
- `--skip-reset` - Don't reset status to pending (advanced)

### Output Example

```
============================================================
Starting sample reprocessing
============================================================

⚠️  WARNING ==================================================
This will reprocess 10 samples through the FULL pipeline:
  - Download video from TikTok
  - Extract audio (WAV + MP3)
  - Generate waveforms
  - Analyze BPM/key
  - Download and store all media
  - This may take a while and consume TikTok API credits
==============================================================

Type 'yes' to continue: yes

[1/10] Processing sample abc-123
  URL: https://www.tiktok.com/@user/video/123
  Creator: @user
  Current status: completed
  Reset sample abc-123 to pending
  ✓ Pipeline triggered for sample abc-123

[2/10] Processing sample def-456
  ...

============================================================
REPROCESSING COMPLETE
============================================================

Total samples: 10
Successfully triggered: 10
Failed: 0
Skipped: 0

💡 Monitor processing progress:
   - Check Inngest dashboard: http://localhost:8288
   - Watch backend logs for processing updates
============================================================
```

### Important Notes

- ⚠️ **Consumes API credits** - Each reprocess uses your TikTok API quota
- ⏱️ **Takes time** - Each sample takes 30-60 seconds to fully process
- 🔄 **Safe to run** - Won't break existing data, just overwrites with fresh data
- 📊 **Monitor progress** - Watch Inngest dashboard at http://localhost:8288

---

## 2. Media Migration Script (Alternative)

### Purpose
Migrates all existing media (videos, thumbnails, cover images, creator avatars) from external TikTok CDN URLs to your own storage infrastructure (R2/S3/GCS).

### When to Use
- After upgrading to the new "self-hosted media" architecture
- When you have samples that were processed before the media migration changes
- To ensure all media is stored in your infrastructure and not relying on TikTok CDN links

### What It Does

The script will:

1. **Sample Media**
   - Download videos from TikTok CDN → Store in `samples/{sample_id}/video.mp4`
   - Download thumbnails → Store in `samples/{sample_id}/thumbnail.jpg`
   - Download cover images → Store in `samples/{sample_id}/cover.jpg`
   - Update database with new URLs

2. **Creator Avatars**
   - Download all 3 avatar sizes (thumb, medium, large)
   - Store in `creators/{creator_id}/avatar_{size}.jpg`
   - Update database with new URLs

3. **Smart Detection**
   - Only migrates URLs that point to TikTok/TikTokCDN
   - Skips items already stored in your infrastructure
   - Provides detailed logging of progress

### How to Run

```bash
# From the backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Run the migration script
python -m scripts.migrate_media_to_storage
```

### Output Example

```
============================================================
Starting media migration to our storage
============================================================

Found 10 samples to process

[1/10] Processing sample...
Processing sample abc-123 (@johndoe)
  Migrating video for sample abc-123
  ✓ Video migrated
✓ Sample abc-123 migrated successfully

...

============================================================
MIGRATION COMPLETE
============================================================

Samples:
  Total: 10
  Migrated: 10
  Failed: 0
```
