# SQL Scripts Directory

This directory contains one-time SQL scripts for data operations that should NOT be in Alembic migrations.

## Guidelines (from CLAUDE.md)

**Use Alembic Migrations For:**
- Schema changes (tables, columns, indexes, constraints)
- Structural modifications
- Changes needed by all environments including new databases

**Use SQL Scripts For:**
- One-time data operations for production
- Bulk data updates or cleanup
- Business logic changes that don't affect schema
- Operations that should be reviewed before running

## Running SQL Scripts

**ALWAYS follow this process:**

```bash
# 1. Review the script first
cat backend/scripts/sql/script-name.sql

# 2. Create a backup
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d-%H%M%S).sql

# 3. Run in transaction (scripts default to ROLLBACK)
psql $DATABASE_URL -f backend/scripts/sql/script-name.sql

# 4. Review output, then edit script to COMMIT if satisfied
# Edit the script: change ROLLBACK to COMMIT at the end
# Then run again to apply changes
psql $DATABASE_URL -f backend/scripts/sql/script-name.sql
```

## Available Scripts

### check_migration_status.sql
Check which migrations have been applied to the database.
Useful for verifying if problematic migrations have already run.

### restore_ultimate_plan_credits.sql
Restore 1500 credits to Ultimate plan subscribers with 0 credits.
Use this if the migration bug affected Ultimate plan users.

### restore_all_subscriber_credits.sql
Restore credits for ALL active subscribers (Basic, Pro, Ultimate) based on their tier.
More comprehensive than the Ultimate-only script.
Includes detailed reporting before and after the update.

### remove_hashtags_from_titles.sql
Clean hashtags from sample titles using PostgreSQL regex.
One-time data cleanup operation that was incorrectly in a migration.
Use only if you need to clean existing data.

## Migration Fixes - Data Operations Moved to SQL Scripts

**Problem:** Two migrations incorrectly contained data operations instead of schema changes.

### 1. Credit Reset Migration (HIGH PRIORITY)
**Migration:** `7459cff6a67f_reset_all_user_credits_to_0_for_.py`
- **Issue:** Reset all user credits to 0 on every migration run
- **Impact:** HIGH - Removed user subscription credits
- **Solution:** ✅ Fixed - Migration now uses `pass`, SQL scripts created for credit restoration

### 2. Hashtag Cleanup Migration (MEDIUM PRIORITY)
**Migration:** `c59169fb76ec_remove_hashtags_from_titles.py`
- **Issue:** Bulk UPDATE to clean hashtags from sample titles
- **Impact:** MEDIUM - One-time data cleanup, less harmful than credit reset
- **Solution:** ✅ Fixed - Migration now uses `pass`, SQL script created: `remove_hashtags_from_titles.sql`

**Why these were problems:**
1. Data operations should be in SQL scripts, not migrations
2. Migrations run on every fresh database (dev, test, CI)
3. Data operations should be reviewable and run explicitly
4. Follows CLAUDE.md guidelines

**For Production:**
```bash
# Check if migration ran
psql $DATABASE_URL -f backend/scripts/sql/check_migration_status.sql

# Restore credits (review first!)
psql $DATABASE_URL -f backend/scripts/sql/restore_all_subscriber_credits.sql
# Review output, edit to COMMIT, then run again
```

## Admin API Alternative

You can also use the admin API endpoint instead of SQL scripts:

```bash
# Add credits to a specific user
curl -X POST https://your-backend.com/api/v1/admin/add-credits \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "clerk_id": "user_xxx",
    "credits": 1500
  }'
```

See `backend/app/api/v1/endpoints/admin.py` for all admin endpoints.
