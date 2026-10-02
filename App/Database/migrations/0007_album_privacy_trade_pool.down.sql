DROP INDEX IF EXISTS idx_user_albums_trade_pool;
DROP INDEX IF EXISTS idx_user_albums_visibility;

CREATE TABLE user_albums_v0006 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    album_id TEXT,
    UNIQUE(user_id, album_id)
);

INSERT INTO user_albums_v0006 (id, user_id, album_id)
SELECT id, user_id, album_id
FROM user_albums;

DROP TABLE user_albums;

ALTER TABLE user_albums_v0006 RENAME TO user_albums;
