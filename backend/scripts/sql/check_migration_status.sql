-- Check if the problematic credit reset migration has been applied
-- This queries the alembic_version table to see migration history

SELECT
    version_num,
    CASE
        WHEN version_num = '7459cff6a67f' THEN '⚠️ PROBLEMATIC MIGRATION (now fixed)'
        ELSE '✅ Normal migration'
    END as status
FROM alembic_version;

-- If you see '7459cff6a67f', the migration already ran
-- But don't worry - it won't run again, and our fix prevents future damage
