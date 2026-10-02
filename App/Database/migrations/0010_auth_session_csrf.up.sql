ALTER TABLE users ADD COLUMN password_scheme TEXT NOT NULL DEFAULT 'legacy_plaintext'
    CHECK (password_scheme IN ('legacy_plaintext', 'werkzeug_scrypt'));

ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 1
    CHECK (auth_version >= 1);

CREATE TABLE login_throttle (
    normalized_username TEXT NOT NULL,
    client_ip TEXT NOT NULL,
    failure_count INTEGER NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    window_started_at TEXT NOT NULL,
    locked_until TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (normalized_username, client_ip)
);

CREATE INDEX idx_login_throttle_locked_until
    ON login_throttle(locked_until);
