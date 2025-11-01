# Database Scripts

This directory contains one-time database operations and utility scripts that should **NOT** be part of the migration history.

## Directory Structure

```
scripts/
├── README.md           # This file
├── sql/                # One-time SQL scripts for data operations
└── python/             # Python utility scripts (future)
```

## When to Use Scripts vs Migrations

### Use Alembic Migrations For:
- **Schema changes** (tables, columns, indexes, constraints)
- **Structural modifications** that must be applied to all environments
- **Repeatable operations** that new databases need
- Changes that are part of the application's evolution

Examples:
- `alembic revision -m "Add subscription table"`
- `alembic revision -m "Add index on user_email"`
- `alembic revision -m "Add NOT NULL constraint to tier column"`

### Use SQL Scripts For:
- **One-time data operations** for production
- **Business logic changes** that don't affect schema
- **Bulk data updates** or cleanup operations
- Operations that should be reviewed before running

Examples:
- Resetting user credits for a launch
- Bulk updating legacy data
- Data migration between systems
- Cleanup of test/duplicate data

## SQL Scripts

### Available Scripts

#### `2025-10-30-reset-credits-for-subscription-launch.sql`
**Purpose:** Reset all user credits to 0 for subscription system launch

**When to run:** Before launching the subscription system in production

**What it does:**
- Creates backup table with current credit values
- Resets all user credits to 0
- Provides rollback instructions

**How to run:**
```bash
# Review the script first
cat backend/scripts/sql/2025-10-30-reset-credits-for-subscription-launch.sql

# Create a database backup (IMPORTANT!)
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d-%H%M%S).sql

# Run the script
psql $DATABASE_URL -f backend/scripts/sql/2025-10-30-reset-credits-for-subscription-launch.sql
```

**Rollback:**
See the ROLLBACK section at the bottom of the script file.

## Best Practices

1. **Always backup before running scripts**
   ```bash
   pg_dump $DATABASE_URL > backup-$(date +%Y%m%d-%H%M%S).sql
   ```

2. **Review scripts before running**
   - Read the entire script
   - Understand what will change
   - Check if rollback is available

3. **Test in staging first**
   - Never run production-only scripts without testing
   - Verify the script works as expected
   - Test the rollback procedure

4. **Document everything**
   - Add comments explaining why the script exists
   - Include the date and purpose
   - Provide rollback instructions

5. **Name scripts descriptively**
   - Use format: `YYYY-MM-DD-description.sql`
   - Include the reason in the filename
   - Make it searchable

## Migration Checklist

Before creating a migration, ask yourself:

- [ ] Does this change the database **structure**? → **Migration**
- [ ] Is this a **one-time** data operation? → **SQL Script**
- [ ] Will new databases need this change? → **Migration**
- [ ] Is this specific to production data? → **SQL Script**
- [ ] Does this modify existing records? → **SQL Script**
- [ ] Does this add/remove tables/columns? → **Migration**

## Common Mistakes

### ❌ DON'T: Put business logic in migrations
```python
# BAD: This is a one-time operation, not a schema change
def upgrade():
    op.execute("UPDATE users SET credits = 0 WHERE credits != 0")
```

### ✅ DO: Use SQL scripts for data operations
```sql
-- GOOD: Explicit one-time script with backup and rollback
-- File: scripts/sql/2025-10-30-reset-credits.sql
BEGIN;
CREATE TABLE users_credits_backup AS ...;
UPDATE users SET credits = 0 WHERE credits != 0;
COMMIT;
```

### ❌ DON'T: Mix schema and data changes
```python
# BAD: Migration doing both schema and data changes
def upgrade():
    op.add_column('users', sa.Column('tier', sa.String(20)))
    op.execute("UPDATE users SET tier = 'free' WHERE tier IS NULL")  # Data operation
```

### ✅ DO: Separate concerns
```python
# GOOD: Migration only handles schema
def upgrade():
    op.add_column('users', sa.Column('tier', sa.String(20), server_default='free'))

# Data backfill done separately via SQL script if needed
```

## Questions?

If you're unsure whether something should be a migration or a script:

1. Would a brand new database need this change? → **Migration**
2. Is this fixing production data? → **SQL Script**
3. Does this change how the application works? → **Migration**
4. Is this a one-time cleanup/update? → **SQL Script**

When in doubt, prefer SQL scripts for safety. They're easier to review, test, and rollback.
