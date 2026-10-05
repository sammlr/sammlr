-- Additive preference only: no membership, pool, inventory or trade backfill.
ALTER TABLE user_albums ADD COLUMN cross_album_mode TEXT NOT NULL
    DEFAULT 'SAME_ALBUM_ONLY'
    CHECK (cross_album_mode IN ('SAME_ALBUM_ONLY', 'CROSS_ALBUM_ALLOWED'));
