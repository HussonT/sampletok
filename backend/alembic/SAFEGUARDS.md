# Migration Safeguards

This document outlines the safeguards in place to prevent data operations from ending up in Alembic migrations.

## The Problem We Solved

**Found:** 2 migrations with data operations (UPDATE/INSERT/DELETE)
- `7459cff6a67f` - Reset user credits to 0
- `c59169fb76ec` - Clean hashtags from titles

**Impact:** Data operations in migrations run automatically on every fresh database (dev, test, CI), causing:
- Lost user credits on redeployments
- Unexpected data modifications
- Inability to review changes before running

**Solution:** All data operations moved to reviewable SQL scripts in `backend/scripts/sql/`

---

## Safeguards Now in Place

### 1. 📋 Migration Template with Checklist

**File:** `backend/alembic/script.py.mako`

Every new migration includes a checklist that must be reviewed and deleted:

```
⚠️ MIGRATION CHECKLIST - DELETE THIS BEFORE COMMITTING ⚠️
═══════════════════════════════════════════════════════════
Before committing, verify:
  ✓ ONLY schema changes (DDL: CREATE, ALTER, DROP)
  ✓ NO data operations (DML: UPDATE, INSERT, DELETE)
  ✓ NO op.execute() with UPDATE/INSERT/DELETE
  ✓ Can run safely on empty database
  ✓ Tested: alembic upgrade head && alembic downgrade -1

Need to modify data? Use backend/scripts/sql/ instead!
See: backend/alembic/MIGRATION_GUIDELINES.md
═══════════════════════════════════════════════════════════
```

**Purpose:** Forces developer to actively review guidelines before committing.

---

### 2. 📖 Comprehensive Guidelines Document

**File:** `backend/alembic/MIGRATION_GUIDELINES.md`

Complete guide with:
- ✅ What SHOULD go in migrations (DDL only)
- ❌ What should NOT go in migrations (DML/data ops)
- 📝 SQL script template
- ✅ Migration creation checklist
- 🚫 Common mistakes with examples
- 📊 Quick reference table

**Key Rule:** If it touches existing data, it's a SQL script.

---

### 3. 🔍 Automated Validation Script

**File:** `backend/scripts/check_migrations.py`

Python script that scans all migrations for dangerous patterns:

```bash
python backend/scripts/check_migrations.py
```

**Detects:**
- `op.execute()` with UPDATE/INSERT/DELETE
- `connection.execute()` with data operations
- Loops over database rows
- Data fetching operations

**Can be used:**
- Manually before committing
- In CI/CD pipeline
- As a pre-commit hook

**Example output:**
```
🔍 Checking 18 migrations for data operations...

✅ All migrations look good! (Schema changes only)

💡 Migrations should only contain DDL (CREATE, ALTER, DROP)
💡 Data operations belong in backend/scripts/sql/
```

---

### 4. 📚 SQL Scripts Directory Structure

**Directory:** `backend/scripts/sql/`

Proper home for all data operations:

```
backend/scripts/sql/
├── README.md                           # Full documentation
├── check_migration_status.sql          # Audit tool
├── remove_hashtags_from_titles.sql     # Data cleanup
├── restore_all_subscriber_credits.sql  # Credit restoration
└── 2025-10-30-reset-credits-for-subscription-launch.sql
```

**All scripts include:**
- Transaction wrapper (BEGIN/COMMIT/ROLLBACK)
- Preview queries before changes
- Verification queries after changes
- Default to ROLLBACK (safe)
- Documentation of purpose and context

---

### 5. 📖 Updated CLAUDE.md

**File:** `CLAUDE.md`

Migration creation process now includes:
1. Generate migration
2. **Review carefully - delete checklist**
3. **Run validation: `python backend/scripts/check_migrations.py`**
4. Test upgrade/downgrade
5. Commit

Direct link to guidelines for all developers.

---

## How to Use These Safeguards

### For New Migrations

```bash
# 1. Generate migration
cd backend
alembic revision --autogenerate -m "Add user preferences table"

# 2. Review the generated file
# - Delete the checklist section at the top
# - Verify ONLY schema changes (no UPDATE/INSERT/DELETE)
# - Remove any auto-generated data operations

# 3. Validate
python scripts/check_migrations.py

# 4. Test
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# 5. Commit
git add alembic/versions/xxxx_add_user_preferences.py
git commit -m "Add user preferences table migration"
```

### For Data Operations

```bash
# 1. Create SQL script (use template from MIGRATION_GUIDELINES.md)
vim backend/scripts/sql/2025-11-01-cleanup-old-samples.sql

# 2. Document in README
# Add entry to backend/scripts/sql/README.md

# 3. Review locally (runs in transaction with ROLLBACK)
psql $DATABASE_URL -f backend/scripts/sql/2025-11-01-cleanup-old-samples.sql

# 4. If output looks good, edit script to COMMIT
# Change ROLLBACK to COMMIT at end of file

# 5. Run again to apply
psql $DATABASE_URL -f backend/scripts/sql/2025-11-01-cleanup-old-samples.sql

# 6. Commit the script (for documentation/future reference)
git add backend/scripts/sql/2025-11-01-cleanup-old-samples.sql
git commit -m "Add SQL script to cleanup old samples"
```

---

## CI/CD Integration (Optional)

Add to your GitHub Actions or CI pipeline:

```yaml
# .github/workflows/migration-check.yml
name: Validate Migrations

on: [pull_request]

jobs:
  check-migrations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate migrations
        run: python backend/scripts/check_migrations.py
```

This ensures no data operations slip through in pull requests.

---

## Quick Reference

| Need to... | Use | Command |
|------------|-----|---------|
| Add table/column | Migration | `alembic revision --autogenerate -m "..."` |
| Modify existing data | SQL Script | Create in `backend/scripts/sql/` |
| Clean up old data | SQL Script | Create in `backend/scripts/sql/` |
| Populate defaults | SQL Script | Create in `backend/scripts/sql/` |
| Check migrations | Validator | `python backend/scripts/check_migrations.py` |
| Read guidelines | Docs | `backend/alembic/MIGRATION_GUIDELINES.md` |

---

## What Changed

### Fixed Migrations
- `7459cff6a67f_reset_all_user_credits_to_0_for_.py` → Now uses `pass`
- `c59169fb76ec_remove_hashtags_from_titles.py` → Now uses `pass`

### New Files
- `backend/alembic/MIGRATION_GUIDELINES.md` - Complete guide
- `backend/alembic/SAFEGUARDS.md` - This document
- `backend/scripts/check_migrations.py` - Validation tool
- `backend/scripts/sql/README.md` - SQL scripts documentation
- `backend/scripts/sql/*.sql` - Replacement SQL scripts

### Updated Files
- `backend/alembic/script.py.mako` - Template with checklist
- `CLAUDE.md` - Updated migration process

---

## Future-Proofing

These safeguards work at multiple levels:

1. **Education** - Guidelines document teaches the why
2. **Prevention** - Template checklist reminds before committing
3. **Detection** - Validation script catches mistakes
4. **Process** - Updated CLAUDE.md ensures steps are followed
5. **Documentation** - Examples and templates make it easy to do right

**Result:** Very difficult to accidentally put data operations in migrations again.

---

## Questions?

- See `backend/alembic/MIGRATION_GUIDELINES.md` for detailed guide
- See `backend/scripts/sql/README.md` for SQL script examples
- Run `python backend/scripts/check_migrations.py` to validate
- Ask: "Does this change the structure or the data?" → Structure = migration, Data = SQL script
