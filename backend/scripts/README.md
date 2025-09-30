# Utility Scripts

This folder contains utility scripts for managing and testing the SampleTok backend.

## Quick Usage

All scripts must be run from the `backend/` directory:

```bash
# Method 1: Direct Python
python scripts/script_name.py [args]

# Method 2: Using helper script (from anywhere)
scripts/run.sh script_name [args]
```

## Cleanup Scripts

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

## Database Management

### `check_db.py`
Check database connection and status.

```bash
python scripts/check_db.py
```

### `check_sample_details.py`
View detailed information about samples in the database.

```bash
python scripts/check_sample_details.py
```

### `add_sample.py`
Manually add a sample to the database.

```bash
python scripts/add_sample.py
```

## Storage/R2 Management

### `check_minio.py`
Check MinIO/S3 connection and bucket status.

```bash
python scripts/check_minio.py
```

### `test_r2_connection.py`
Test connection to Cloudflare R2.

```bash
python scripts/test_r2_connection.py
```

### `create_bucket.py`
Create S3/R2 bucket if it doesn't exist.

```bash
python scripts/create_bucket.py
```

## Testing Scripts

### `test_api.py`
Test API endpoints.

```bash
python scripts/test_api.py
```

### `test_rapidapi.py`
Test RapidAPI TikTok integration.

```bash
python scripts/test_rapidapi.py
```

### `test_full_pipeline.py`
Test the complete TikTok processing pipeline.

```bash
python scripts/test_full_pipeline.py
```

### `test_function_direct.py`
Test Inngest functions directly.

```bash
python scripts/test_function_direct.py
```

## Notes

- All scripts should be run from the `backend/` directory
- Make sure your `.env` file is configured properly
- Some scripts may require the database and/or storage services to be running