CREATE TEMP TABLE s32_backout_guard (
    secure_password_count INTEGER NOT NULL CHECK (secure_password_count = 0)
);

INSERT INTO s32_backout_guard (secure_password_count)
SELECT COUNT(*) FROM users WHERE password_scheme='werkzeug_scrypt';

DROP TABLE s32_backout_guard;
DROP INDEX IF EXISTS idx_login_throttle_locked_until;
DROP TABLE login_throttle;
ALTER TABLE users DROP COLUMN auth_version;
ALTER TABLE users DROP COLUMN password_scheme;
