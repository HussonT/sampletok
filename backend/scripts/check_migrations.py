#!/usr/bin/env python3
"""
Check Alembic migrations for data operations that should be SQL scripts instead.

This script scans migration files for common patterns that indicate data
operations (UPDATE, INSERT, DELETE) which violate the migration guidelines.

Usage:
    python backend/scripts/check_migrations.py

Exit codes:
    0 - All migrations are valid (schema changes only)
    1 - Found migrations with data operations

Can be used as a pre-commit hook or CI check.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


# Patterns that indicate data operations (not allowed in migrations)
DANGEROUS_PATTERNS = [
    (r'execute\([^)]*UPDATE\s+', 'op.execute() with UPDATE statement'),
    (r'execute\([^)]*INSERT\s+', 'op.execute() with INSERT statement'),
    (r'execute\([^)]*DELETE\s+', 'op.execute() with DELETE statement'),
    (r'\.execute\([^)]*UPDATE\s+', 'connection.execute() with UPDATE'),
    (r'\.execute\([^)]*INSERT\s+', 'connection.execute() with INSERT'),
    (r'\.execute\([^)]*DELETE\s+', 'connection.execute() with DELETE'),
    (r'fetchall\(\)', 'Fetching data from database (likely for processing)'),
    (r'for\s+\w+.*in.*execute\(', 'Loop over database rows (data operation)'),
]

# Patterns that are OK (DDL operations)
SAFE_PATTERNS = [
    r'ondelete=',  # Foreign key cascade
    r'server_default=',  # Column defaults
    r'op\.create_table',
    r'op\.drop_table',
    r'op\.add_column',
    r'op\.drop_column',
    r'op\.create_index',
    r'op\.drop_index',
    r'op\.create_constraint',
    r'op\.drop_constraint',
]


def is_safe_pattern(line: str) -> bool:
    """Check if line matches a safe DDL pattern."""
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in SAFE_PATTERNS)


def check_migration_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    Check a migration file for data operations.

    Returns:
        List of (line_number, line_content, issue_description)
    """
    issues = []

    with open(filepath, 'r') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        # Skip if it's a safe DDL pattern
        if is_safe_pattern(line):
            continue

        # Check for dangerous patterns
        for pattern, description in DANGEROUS_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append((line_num, line.strip(), description))
                break

    return issues


def main():
    """Scan all migrations and report issues."""
    # Get migrations directory
    script_dir = Path(__file__).parent.parent
    migrations_dir = script_dir / 'alembic' / 'versions'

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return 1

    # Find all migration files
    migration_files = sorted(migrations_dir.glob('*.py'))
    migration_files = [f for f in migration_files if f.name != '__init__.py']

    if not migration_files:
        print("⚠️  No migration files found")
        return 0

    print(f"🔍 Checking {len(migration_files)} migrations for data operations...\n")

    # Check each migration
    total_issues = 0
    problematic_files = []

    for filepath in migration_files:
        issues = check_migration_file(filepath)

        if issues:
            total_issues += len(issues)
            problematic_files.append(filepath.name)

            print(f"❌ {filepath.name}")
            for line_num, line_content, description in issues:
                print(f"   Line {line_num}: {description}")
                print(f"   → {line_content[:80]}{'...' if len(line_content) > 80 else ''}")
            print()

    # Print summary
    print("═" * 70)
    if total_issues == 0:
        print("✅ All migrations look good! (Schema changes only)")
        print("\n💡 Migrations should only contain DDL (CREATE, ALTER, DROP)")
        print("💡 Data operations belong in backend/scripts/sql/")
        return 0
    else:
        print(f"❌ Found {total_issues} potential issues in {len(problematic_files)} files:")
        for filename in problematic_files:
            print(f"   • {filename}")
        print("\n⚠️  Migrations should ONLY contain schema changes (DDL)")
        print("⚠️  Data operations (UPDATE, INSERT, DELETE) must go in backend/scripts/sql/")
        print("\n📖 See: backend/alembic/MIGRATION_GUIDELINES.md")
        return 1


if __name__ == '__main__':
    sys.exit(main())
