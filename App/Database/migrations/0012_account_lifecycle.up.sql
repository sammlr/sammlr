ALTER TABLE users ADD COLUMN account_state TEXT NOT NULL DEFAULT 'active'
    CHECK (account_state IN ('active', 'deactivated', 'anonymized'));

CREATE INDEX idx_s35_users_account_state
    ON users(account_state, id);
