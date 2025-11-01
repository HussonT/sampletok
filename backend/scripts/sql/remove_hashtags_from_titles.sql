-- Remove hashtags from sample titles
-- This is a data cleanup operation that was incorrectly placed in a migration
-- Use this script if you need to clean hashtags from existing sample titles
--
-- IMPORTANT: Review before running in production!
-- Create a backup first: pg_dump $DATABASE_URL > backup-$(date +%Y%m%d-%H%M%S).sql

BEGIN;

-- Show samples with hashtags before cleanup
SELECT
    id,
    title AS original_title,
    LENGTH(title) AS original_length,
    (title ~ '#\w+')::int AS has_hashtags
FROM samples
WHERE title IS NOT NULL
  AND title LIKE '%#%'
ORDER BY created_at DESC
LIMIT 20;

-- Count affected samples
SELECT
    COUNT(*) AS total_samples_with_hashtags,
    COUNT(DISTINCT creator_id) AS unique_creators_affected
FROM samples
WHERE title IS NOT NULL
  AND title LIKE '%#%';

-- Clean hashtags from titles
-- PostgreSQL regex approach: remove #word patterns and clean up spaces
UPDATE samples
SET title = TRIM(REGEXP_REPLACE(
    REGEXP_REPLACE(title, '#\w+', '', 'g'),  -- Remove #hashtags
    '\s+', ' ', 'g'                           -- Clean up multiple spaces
))
WHERE title IS NOT NULL
  AND title LIKE '%#%';

-- Show results after cleanup
SELECT
    id,
    title AS cleaned_title,
    LENGTH(title) AS new_length
FROM samples
WHERE id IN (
    SELECT id FROM samples
    WHERE title IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 20
);

-- Verification: Check if any hashtags remain
SELECT
    COUNT(*) AS remaining_samples_with_hashtags
FROM samples
WHERE title IS NOT NULL
  AND title LIKE '%#%';

-- COMMIT or ROLLBACK
-- Review the output above, then uncomment COMMIT to apply
-- COMMIT;
ROLLBACK;
