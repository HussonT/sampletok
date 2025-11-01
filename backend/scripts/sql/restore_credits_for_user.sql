-- Restore credits for a specific user by Clerk ID
-- Replace 'YOUR_CLERK_ID' with the actual clerk_user_id
--
-- IMPORTANT: Review and update the WHERE clause before running!

BEGIN;

-- Show current user state
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
LEFT JOIN subscriptions s ON s.user_id = u.id
WHERE u.clerk_user_id = 'YOUR_CLERK_ID';  -- ⚠️ REPLACE THIS

-- Update credits based on subscription tier
UPDATE users u
SET credits = s.monthly_credits
FROM subscriptions s
WHERE s.user_id = u.id
  AND u.clerk_user_id = 'YOUR_CLERK_ID'  -- ⚠️ REPLACE THIS
  AND s.status IN ('active', 'past_due');

-- Show updated state
SELECT
    u.id,
    u.email,
    u.clerk_user_id,
    u.credits AS new_credits,
    s.tier,
    s.monthly_credits,
    s.status AS subscription_status
FROM users u
LEFT JOIN subscriptions s ON s.user_id = u.id
WHERE u.clerk_user_id = 'YOUR_CLERK_ID';  -- ⚠️ REPLACE THIS

-- COMMIT or ROLLBACK
-- Review the output above, then uncomment COMMIT to apply
-- COMMIT;
ROLLBACK;
