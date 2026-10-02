CREATE TABLE sammlr_news (
    news_key TEXT PRIMARY KEY,
    event_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    target_path TEXT,
    published_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_key) REFERENCES feed_events(event_key) ON DELETE RESTRICT,
    CHECK (length(trim(news_key)) > 0),
    CHECK (length(trim(event_key)) > 0),
    CHECK (length(trim(title)) > 0),
    CHECK (length(trim(body)) > 0),
    CHECK (
        target_path IS NULL
        OR (length(trim(target_path)) > 0 AND substr(target_path, 1, 1) = '/')
    ),
    CHECK (length(trim(published_at)) > 0)
);

CREATE INDEX idx_cb007_feed_events_canonical_time
    ON feed_events(occurred_at DESC, event_key DESC);

CREATE INDEX idx_cb007_news_time
    ON sammlr_news(published_at DESC, news_key DESC);

CREATE TRIGGER cb007_feed_event_type_insert
BEFORE INSERT ON feed_events
WHEN NEW.event_type NOT IN (
    'album_started', 'album_completed', 'trophy_unlocked', 'sammlr_news'
)
BEGIN
    SELECT RAISE(ABORT, 'unsupported CB-007 feed event type');
END;

CREATE TRIGGER cb007_feed_event_type_update
BEFORE UPDATE OF event_type ON feed_events
WHEN NEW.event_type NOT IN (
    'album_started', 'album_completed', 'trophy_unlocked', 'sammlr_news'
)
BEGIN
    SELECT RAISE(ABORT, 'unsupported CB-007 feed event type');
END;
