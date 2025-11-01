-- Restore credits for Ultimate plan subscribers
-- This script grants 1500 credits to users with active Ultimate subscriptions
-- who currently have 0 credits (likely affected by the migration bug)
--
-- IMPORTANT: Review this script before running in production!
-- Create a backup first: pg_dump $DATABASE_URL > backup-$(date +%Y%m%d-%H%M%S).sql

BEGIN;

-- Show affected users before updating
SELECT
    u.id,
    u.email,
    u.clerk_user_id,
    u.credits AS current_credits,
    s.tier,
    s.monthly_credits,
    s.status AS subscription_status
FROM users u
JOIN subscriptions s ON s.user_id = u.id
WHERE s.tier = 'ultimate'
  AND s.status = 'active'
  AND u.credits = 0;

-- Update credits for active Ultimate plan users with 0 credits
UPDATE users u
SET credits = s.monthly_credits
FROM subscriptions s
WHERE s.user_id = u.id
  AND s.tier = 'ultimate'
  AND s.status = 'active'
  AND u.credits = 0;

-- Show updated users
SELECT
    u.id,
    u.email,
    u.clerk_user_id,
    u.credits AS new_credits,
    s.tier,
    s.monthly_credits,
    s.status AS subscription_status
FROM users u
JOIN subscriptions s ON s.user_id = u.id
WHERE s.tier = 'ultimate'
  AND s.status = 'active';

-- COMMIT or ROLLBACK
-- Uncomment COMMIT to apply changes, or ROLLBACK to cancel
-- COMMIT;
ROLLBACK;
