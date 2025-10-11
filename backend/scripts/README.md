# Utility Scripts

This folder contains production utility scripts for managing the SampleTok backend.

## Quick Usage

All scripts must be run from the `backend/` directory:

```bash
# Method 1: Direct Python
python scripts/script_name.py [args]

# Method 2: Using helper script (from anywhere)
scripts/run.sh script_name [args]
```

## Available Scripts

### `backfill_creators.py`
Backfill creator information for existing samples that don't have linked TikTok creator records.

```bash
python scripts/backfill_creators.py
```

This script will:
- Find samples with creator usernames but no creator link
- Fetch creator info from TikTok API (with caching)
- Link samples to creator records

### `cleanup_orphaned_samples.py`
Clean up incomplete/orphaned sample records from the database.

```bash
# Show statistics
python scripts/cleanup_orphaned_samples.py --stats

# Preview what would be deleted (dry run)
python scripts/cleanup_orphaned_samples.py --dry-run

# Delete orphaned samples
python scripts/cleanup_orphaned_samples.py --delete

# Delete samples older than 7 days
python scripts/cleanup_orphaned_samples.py --delete --days 7
```

### `cleanup_duplicates.py`
Clean up duplicate sample records.

```bash
python scripts/cleanup_duplicates.py
```

## Testing

All tests have been moved to the `tests/` directory and use pytest.

Run tests with:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=app tests/

# Run with verbose output
pytest -v
```

Available test suites:
- `tests/test_api.py` - API endpoint tests
- `tests/test_rapidapi.py` - TikTok downloader integration tests
- `tests/test_storage.py` - S3/R2 storage tests
- `tests/test_pipeline.py` - Full processing pipeline integration tests

## Notes

- All scripts should be run from the `backend/` directory
- Make sure your `.env` file is configured properly
- Some scripts may require the database and/or storage services to be running