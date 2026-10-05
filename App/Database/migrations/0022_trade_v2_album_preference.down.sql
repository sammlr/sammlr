-- Never silently discard an explicit cross-album consent during backout.
CREATE TEMP TABLE trade_v2_preference_backout_guard (safe INTEGER NOT NULL CHECK (safe=1));
INSERT INTO trade_v2_preference_backout_guard
SELECT CASE WHEN EXISTS (
    SELECT 1 FROM user_albums WHERE cross_album_mode <> 'SAME_ALBUM_ONLY'
) THEN 0 ELSE 1 END;
DROP TABLE trade_v2_preference_backout_guard;
ALTER TABLE user_albums DROP COLUMN cross_album_mode;
