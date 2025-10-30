-- Reset the stuck collection and refund credits
BEGIN;

-- Get current stats
SELECT 
    'BEFORE' as stage,
    c.id,
    c.name,
    c.status,
    c.total_video_count,
    c.processed_count,
    u.credits as user_credits
FROM collections c
JOIN users u ON c.user_id = u.id
WHERE c.id = '2a3960d1-f762-4947-8f50-f2a736dd1bf6';

-- Calculate refund amount
WITH refund_calc AS (
    SELECT 
        user_id,
        total_video_count - COALESCE(processed_count, 0) as credits_to_refund
    FROM collections
    WHERE id = '2a3960d1-f762-4947-8f50-f2a736dd1bf6'
)
-- Refund credits
UPDATE users
SET credits = credits + (SELECT credits_to_refund FROM refund_calc)
WHERE id = (SELECT user_id FROM refund_calc);

-- Reset collection
UPDATE collections
SET 
    status = 'pending',
    processed_count = 0,
    error_message = NULL,
    current_cursor = 0,
    started_at = NULL,
    completed_at = NULL
WHERE id = '2a3960d1-f762-4947-8f50-f2a736dd1bf6';

-- Show results
SELECT 
    'AFTER' as stage,
    c.id,
    c.name,
    c.status,
    c.total_video_count,
    c.processed_count,
    u.credits as user_credits
FROM collections c
JOIN users u ON c.user_id = u.id
WHERE c.id = '2a3960d1-f762-4947-8f50-f2a736dd1bf6';

COMMIT;
