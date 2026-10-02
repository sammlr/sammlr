DROP TABLE IF EXISTS temp.cb007_news_backout_guard;

CREATE TEMP TABLE cb007_news_backout_guard (
    news_count INTEGER NOT NULL CHECK (news_count = 0)
);

INSERT INTO cb007_news_backout_guard (news_count)
SELECT COUNT(*) FROM sammlr_news;

DROP TABLE cb007_news_backout_guard;
DROP TRIGGER cb007_feed_event_type_update;
DROP TRIGGER cb007_feed_event_type_insert;
DROP INDEX idx_cb007_news_time;
DROP INDEX idx_cb007_feed_events_canonical_time;
DROP TABLE sammlr_news;
