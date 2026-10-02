DROP TABLE IF EXISTS temp.s35_account_lifecycle_backout_guard;

CREATE TEMP TABLE s35_account_lifecycle_backout_guard (
    non_active_count INTEGER NOT NULL CHECK (non_active_count = 0)
);

INSERT INTO s35_account_lifecycle_backout_guard (non_active_count)
SELECT COUNT(*) FROM users WHERE account_state <> 'active';

DROP TABLE s35_account_lifecycle_backout_guard;
DROP INDEX idx_s35_users_account_state;
ALTER TABLE users DROP COLUMN account_state;
