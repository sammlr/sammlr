DROP TABLE IF EXISTS temp.cb006_profile_privacy_backout_guard;

CREATE TEMP TABLE cb006_profile_privacy_backout_guard (
    private_count INTEGER NOT NULL CHECK (private_count = 0)
);

INSERT INTO cb006_profile_privacy_backout_guard (private_count)
SELECT COUNT(*) FROM users WHERE profile_privacy <> 'public';

DROP TABLE cb006_profile_privacy_backout_guard;
ALTER TABLE users DROP COLUMN profile_privacy;
