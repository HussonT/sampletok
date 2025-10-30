-- Reset all stuck collections for husson.tom@gmail.com
BEGIN;

-- Show user info
SELECT
    'USER INFO' as info,
    id,
    email,
    credits as current_credits,
    created_at
FROM users
WHERE email = 'husson.tom@gmail.com';

-- Show stuck collections
SELECT
    'STUCK COLLECTIONS' as info,
    c.id,
    c.name,
    c.status,
    c.total_video_count,
    COALESCE(c.processed_count, 0) as processed_count,
    c.total_video_count - COALESCE(c.processed_count, 0) as credits_to_refund
FROM collections c
JOIN users u ON c.user_id = u.id
WHERE u.email = 'husson.tom@gmail.com'
AND c.status IN ('pending', 'processing', 'failed');

-- Calculate total refund
WITH user_collections AS (
    SELECT
        u.id as user_id,
        SUM(c.total_video_count - COALESCE(c.processed_count, 0)) as total_refund
    FROM collections c
    JOIN users u ON c.user_id = u.id
    WHERE u.email = 'husson.tom@gmail.com'
    AND c.status IN ('pending', 'processing', 'failed')
    GROUP BY u.id
)
-- Refund credits
UPDATE users
SET credits = credits + COALESCE((SELECT total_refund FROM user_collections WHERE user_id = users.id), 0)
WHERE email = 'husson.tom@gmail.com';

-- Reset all stuck collections
UPDATE collections
SET
    status = 'pending',
    processed_count = 0,
    error_message = NULL,
    current_cursor = 0,
    started_at = NULL,
    completed_at = NULL
FROM users u
WHERE collections.user_id = u.id
AND u.email = 'husson.tom@gmail.com'
AND collections.status IN ('pending', 'processing', 'failed');

-- Show final results
SELECT
    'AFTER RESET' as info,
    c.id,
    c.name,
    c.status,
    c.total_video_count,
    c.processed_count,
    u.credits as user_credits
FROM collections c
JOIN users u ON c.user_id = u.id
WHERE u.email = 'husson.tom@gmail.com'
ORDER BY c.created_at DESC
LIMIT 10;

COMMIT;
