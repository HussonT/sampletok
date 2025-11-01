-- Restore credits for ALL active subscribers (Basic, Pro, Ultimate)
-- This script grants appropriate credits based on subscription tier
-- for users who currently have 0 credits (likely affected by migration bug)
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
    s.status AS subscription_status,
    s.current_period_start,
    s.current_period_end
FROM users u
JOIN subscriptions s ON s.user_id = u.id
WHERE s.status IN ('active', 'past_due')  -- Include past_due to be generous
  AND u.credits = 0
ORDER BY s.tier, u.email;

-- Count affected users by tier
SELECT
    s.tier,
    COUNT(*) as affected_users,
    SUM(s.monthly_credits) as total_credits_to_restore
FROM users u
JOIN subscriptions s ON s.user_id = u.id
WHERE s.status IN ('active', 'past_due')
  AND u.credits = 0
GROUP BY s.tier;

-- Update credits for all active subscribers with 0 credits
UPDATE users u
SET credits = s.monthly_credits
FROM subscriptions s
WHERE s.user_id = u.id
  AND s.status IN ('active', 'past_due')
  AND u.credits = 0;

-- Show summary after update
SELECT
    s.tier,
    COUNT(*) as users_restored,
    AVG(u.credits) as avg_credits,
    SUM(u.credits) as total_credits
FROM users u
JOIN subscriptions s ON s.user_id = u.id
WHERE s.status IN ('active', 'past_due')
GROUP BY s.tier
ORDER BY s.tier;

-- Verification: Check if anyone still has 0 credits with active subscription
SELECT
    COUNT(*) as remaining_zero_credit_subscribers
FROM users u
JOIN subscriptions s ON s.user_id = u.id
WHERE s.status IN ('active', 'past_due')
  AND u.credits = 0;

-- COMMIT or ROLLBACK
-- Review the output above, then uncomment COMMIT to apply changes
-- COMMIT;
ROLLBACK;
