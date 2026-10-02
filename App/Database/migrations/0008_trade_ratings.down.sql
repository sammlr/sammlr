CREATE TEMP TABLE s28_backout_guard (
    rating_count INTEGER NOT NULL CHECK (rating_count = 0)
);

INSERT INTO s28_backout_guard (rating_count)
    SELECT COUNT(*) FROM trade_ratings;

DROP TABLE s28_backout_guard;

DROP TRIGGER IF EXISTS trade_ratings_no_update;
DROP TRIGGER IF EXISTS trade_ratings_no_delete;
DROP INDEX IF EXISTS idx_trade_ratings_rated_user;
DROP TABLE trade_ratings;
