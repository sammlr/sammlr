ALTER TABLE user_albums
    ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
    CHECK (visibility IN ('public', 'friends', 'private'));

ALTER TABLE user_albums
    ADD COLUMN trade_pool_enabled INTEGER NOT NULL DEFAULT 1
    CHECK (trade_pool_enabled IN (0, 1));

CREATE INDEX idx_user_albums_visibility
    ON user_albums(user_id, visibility, album_id);

CREATE INDEX idx_user_albums_trade_pool
    ON user_albums(album_id, trade_pool_enabled, user_id);
