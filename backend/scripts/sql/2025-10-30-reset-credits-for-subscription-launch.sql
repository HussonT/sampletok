/*
 * One-time operation: Reset all user credits for subscription system launch
 *
 * Date: 2025-10-30
 * Purpose: Transition from free credits to subscription-based credit system
 *
 * IMPORTANT: This is a destructive operation. Review carefully before running.
 *
 * Instructions:
 *   1. Review this script and ensure you understand what it does
 *   2. Ensure you have a database backup before proceeding
 *   3. Run this script manually when you're ready to launch subscriptions:
 *      psql $DATABASE_URL -f backend/scripts/sql/2025-10-30-reset-credits-for-subscription-launch.sql
 *
 * What this does:
 *   - Creates a backup table with current credit values
 *   - Resets all user credits to 0
 *   - Users will need to subscribe to receive credits going forward
 *
 * Recovery:
 *   - If you need to undo this operation, see the rollback section at the bottom
 */

-- Start transaction
BEGIN;

-- Create backup table for credit values
CREATE TABLE IF NOT EXISTS users_credits_backup_20251030 (
    id UUID PRIMARY KEY,
    credits INTEGER NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    backed_up_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backup all users with non-zero credits
INSERT INTO users_credits_backup_20251030 (id, credits, created_at, updated_at)
SELECT id, credits, created_at, updated_at
FROM users
WHERE credits != 0
ON CONFLICT (id) DO NOTHING;  -- In case table already exists from a previous run

-- Show what will be reset
DO $$
DECLARE
    affected_count INTEGER;
    total_credits INTEGER;
BEGIN
    SELECT COUNT(*), COALESCE(SUM(credits), 0)
    INTO affected_count, total_credits
    FROM users
    WHERE credits != 0;

    RAISE NOTICE 'Resetting credits for % users (total: % credits)', affected_count, total_credits;
END $$;

-- Reset all user credits to 0
UPDATE users
SET credits = 0
WHERE credits != 0;

-- Verify the operation
DO $$
DECLARE
    remaining_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO remaining_count
    FROM users
    WHERE credits != 0;

    IF remaining_count > 0 THEN
        RAISE EXCEPTION 'Credit reset failed: % users still have credits', remaining_count;
    END IF;

    RAISE NOTICE 'Success: All user credits reset to 0';
END $$;

-- Commit transaction
COMMIT;

RAISE NOTICE 'Backup table "users_credits_backup_20251030" created with original credit values';
RAISE NOTICE 'To rollback this operation, see the ROLLBACK section at the bottom of this file';

/*
 * ============================================================================
 * ROLLBACK INSTRUCTIONS
 * ============================================================================
 *
 * If you need to restore the original credit values, run the following:
 *
 * BEGIN;
 *
 * -- Restore credits from backup
 * UPDATE users
 * SET credits = backup.credits
 * FROM users_credits_backup_20251030 backup
 * WHERE users.id = backup.id;
 *
 * -- Verify restoration
 * DO $$
 * DECLARE
 *     restored_count INTEGER;
 * BEGIN
 *     SELECT COUNT(*)
 *     INTO restored_count
 *     FROM users u
 *     INNER JOIN users_credits_backup_20251030 b ON u.id = b.id
 *     WHERE u.credits = b.credits;
 *
 *     RAISE NOTICE 'Restored credits for % users', restored_count;
 * END $$;
 *
 * COMMIT;
 *
 * -- Optional: Drop backup table after successful restoration
 * -- DROP TABLE users_credits_backup_20251030;
 *
 */
