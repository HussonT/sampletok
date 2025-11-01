# Migration Guidelines

**CRITICAL:** Read this before creating any Alembic migration!

## Rule #1: Migrations are ONLY for Schema Changes

### ✅ DO use migrations for:
- Creating/dropping tables
- Adding/removing/modifying columns
- Adding/removing indexes
- Adding/removing constraints (foreign keys, check constraints, unique)
- Changing column types or nullability
- Any DDL (Data Definition Language) operations

### ❌ DON'T use migrations for:
- UPDATE operations on existing data
- INSERT operations to populate data
- DELETE operations to clean up data
- Any DML (Data Manipulation Language) operations
- Business logic changes
- One-time data cleanup
- Bulk updates

## Rule #2: If It Touches Data, It's a SQL Script

**Data operations MUST go in `backend/scripts/sql/`**

### Examples of what goes in SQL scripts:
```sql
-- ❌ NEVER in migrations
UPDATE users SET credits = 0;
UPDATE samples SET title = TRIM(title);
INSERT INTO settings VALUES (...);
DELETE FROM old_table WHERE created_at < '2024-01-01';

-- ✅ ALWAYS in backend/scripts/sql/
```

## How to Create Data Operation Scripts

1. **Create file:** `backend/scripts/sql/YYYY-MM-DD-description.sql`
2. **Use transaction with ROLLBACK by default:**
   ```sql
   BEGIN;

   -- Show what will change
   SELECT ...;

   -- Make changes
   UPDATE ...;

   -- Verify changes
   SELECT ...;

   -- COMMIT; -- Uncomment after reviewing
   ROLLBACK;  -- Default to safe rollback
   ```

3. **Document in `backend/scripts/sql/README.md`**
4. **Run manually when ready:** `psql $DATABASE_URL -f script.sql`

## Migration Creation Checklist

Before running `alembic revision --autogenerate`:

- [ ] Am I only changing the **structure** of tables?
- [ ] Do I need to **modify existing data**? → Use SQL script instead
- [ ] Does this need to run **once in production**? → Use SQL script instead
- [ ] Can this safely run on **empty databases**? (Yes = migration, No = SQL script)

After creating migration:

- [ ] Review the generated migration file
- [ ] Check for `UPDATE`, `INSERT`, `DELETE` statements
- [ ] Verify it only contains `op.create_table()`, `op.add_column()`, etc.
- [ ] Test on fresh database: `alembic downgrade -1 && alembic upgrade head`

## Common Mistakes

### ❌ Mistake #1: "One-time" data operations in migrations
```python
def upgrade():
    # BAD: This runs on every fresh database!
    op.execute("UPDATE users SET credits = 0")
```

**Why it's bad:** Runs every time someone sets up a fresh database (dev, test, CI, new deployments).

**Fix:** Move to `backend/scripts/sql/reset-credits.sql`

---

### ❌ Mistake #2: Data cleanup in migrations
```python
def upgrade():
    connection = op.get_bind()
    samples = connection.execute("SELECT id, title FROM samples")
    for sample_id, title in samples:
        cleaned = clean_data(title)
        connection.execute(f"UPDATE samples SET title = '{cleaned}' WHERE id = {sample_id}")
```

**Why it's bad:**
- Runs on empty test databases (errors)
- Can't be reviewed before running
- Mixes schema and data concerns

**Fix:** Move to `backend/scripts/sql/clean-sample-titles.sql`

---

### ❌ Mistake #3: Assuming migrations run once
```python
def upgrade():
    # "This will only run once in prod, right?"
    op.execute("INSERT INTO settings VALUES ('launched', true)")
```

**Why it's bad:** Also runs in dev, test, CI, staging, new teammate's setup.

**Fix:** Move to `backend/scripts/sql/mark-production-launched.sql`

---

## Quick Reference

| Operation | Where It Goes | Example |
|-----------|---------------|---------|
| Add table | Migration | `op.create_table('users', ...)` |
| Add column | Migration | `op.add_column('users', Column('email'))` |
| Add index | Migration | `op.create_index('idx_email', 'users', ['email'])` |
| Update data | SQL Script | `UPDATE users SET verified = true` |
| Clean data | SQL Script | `UPDATE samples SET title = TRIM(title)` |
| Populate defaults | SQL Script | `INSERT INTO settings VALUES (...)` |
| Reset for launch | SQL Script | `UPDATE users SET credits = 0` |

## Template for SQL Scripts

Copy this template when creating new data operation scripts:

```sql
-- Description: What this script does
-- Date: YYYY-MM-DD
-- Context: Why this is needed
--
-- IMPORTANT: Review before running in production!
-- Backup first: pg_dump $DATABASE_URL > backup-$(date +%Y%m%d-%H%M%S).sql

BEGIN;

-- Show current state
SELECT
    COUNT(*) as total_affected,
    -- other relevant stats
FROM target_table
WHERE condition;

-- Perform operation
UPDATE target_table
SET column = new_value
WHERE condition;

-- Verify results
SELECT
    COUNT(*) as rows_updated,
    -- verify the change worked
FROM target_table
WHERE new_condition;

-- COMMIT or ROLLBACK
-- Review output above, then uncomment COMMIT
-- COMMIT;
ROLLBACK;
```

## Getting Help

If you're unsure whether something should be a migration or SQL script, ask yourself:

1. **Does this change the database structure?** → Migration
2. **Does this modify existing data?** → SQL Script
3. **Would this make sense on an empty database?** → Yes = Migration, No = SQL Script

**When in doubt:** Use a SQL script. It's safer and more reviewable.

## Further Reading

- [CLAUDE.md](../../CLAUDE.md) - Project guidelines
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [backend/scripts/sql/README.md](../scripts/sql/README.md) - SQL script examples
