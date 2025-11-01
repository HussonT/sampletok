# Alembic Migrations

Database migration management for Sampletok backend.

## ⚠️ Before Creating a Migration

**READ THIS FIRST:** [MIGRATION_GUIDELINES.md](./MIGRATION_GUIDELINES.md)

**Key Rule:** Migrations are ONLY for schema changes (DDL). Data operations go in `backend/scripts/sql/`.

## Quick Start

### Create a new migration

```bash
cd backend

# 1. Modify your SQLAlchemy models in app/models/
# 2. Generate migration
alembic revision --autogenerate -m "Add user preferences table"

# 3. Review the generated file (delete checklist, verify schema-only)
# 4. Validate
python scripts/check_migrations.py

# 5. Test
alembic upgrade head
alembic downgrade -1

# 6. Commit
git add alembic/versions/xxx_add_user_preferences.py
git commit -m "Add user preferences table migration"
```

### Apply migrations

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current

# View history
alembic history
```

### Validate migrations

```bash
# Check all migrations for data operations
python backend/scripts/check_migrations.py
```

## 📚 Documentation

- **[MIGRATION_GUIDELINES.md](./MIGRATION_GUIDELINES.md)** - Complete guide on what goes where
- **[SAFEGUARDS.md](./SAFEGUARDS.md)** - Safeguards preventing data operations in migrations
- **[script.py.mako](./script.py.mako)** - Migration template (includes checklist)

## ❌ Common Mistakes

### ❌ Wrong: Data operation in migration
```python
def upgrade():
    op.execute("UPDATE users SET credits = 0")  # DON'T DO THIS
```

### ✅ Right: Data operation in SQL script
```bash
# Create backend/scripts/sql/2025-11-01-reset-credits.sql instead
psql $DATABASE_URL -f backend/scripts/sql/2025-11-01-reset-credits.sql
```

## 🔍 Quick Reference

| I need to... | What to do |
|--------------|------------|
| Add a table | `alembic revision --autogenerate -m "Add table"` |
| Add a column | `alembic revision --autogenerate -m "Add column"` |
| Update existing data | Create SQL script in `backend/scripts/sql/` |
| Clean up old data | Create SQL script in `backend/scripts/sql/` |
| Populate defaults | Create SQL script in `backend/scripts/sql/` |

## 🚨 Migration Failures

If a migration fails:

```bash
# Check current state
alembic current

# Check what went wrong
alembic history --verbose

# Mark migration as failed (allows retry)
alembic stamp head-1

# Fix the migration file, then retry
alembic upgrade head
```

## 🔐 Production Deployment

Migrations run automatically in production via the Docker startup script:

```bash
# In runit.sh
alembic upgrade head
```

No manual intervention needed - migrations apply on deployment.

## ✅ Validation

Before committing migrations, always run:

```bash
python backend/scripts/check_migrations.py
```

This ensures your migration only contains schema changes.

## 📖 More Info

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Project Guidelines (CLAUDE.md)](../../CLAUDE.md)
- [SQL Scripts README](../scripts/sql/README.md)
