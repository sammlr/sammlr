CREATE TABLE trade_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    rater_user_id INTEGER NOT NULL,
    rated_user_id INTEGER NOT NULL,
    stars INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE RESTRICT,
    CHECK (rater_user_id <> rated_user_id),
    CHECK (stars BETWEEN 1 AND 5),
    UNIQUE (trade_id, rater_user_id),
    UNIQUE (trade_id, rated_user_id)
);

CREATE INDEX idx_trade_ratings_rated_user
    ON trade_ratings(rated_user_id, created_at, id);

CREATE TRIGGER trade_ratings_no_update
BEFORE UPDATE ON trade_ratings
BEGIN
    SELECT RAISE(ABORT, 'trade ratings are final');
END;

CREATE TRIGGER trade_ratings_no_delete
BEFORE DELETE ON trade_ratings
BEGIN
    SELECT RAISE(ABORT, 'trade ratings are final');
END;
