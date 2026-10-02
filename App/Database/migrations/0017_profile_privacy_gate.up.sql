ALTER TABLE users
    ADD COLUMN profile_privacy TEXT NOT NULL DEFAULT 'public'
    CHECK (profile_privacy IN ('public', 'private'));
