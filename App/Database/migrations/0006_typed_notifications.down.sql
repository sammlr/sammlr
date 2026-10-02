CREATE TEMP TABLE s23_backout_guard (
    typed_notification_count INTEGER NOT NULL
        CHECK (typed_notification_count = 0)
);

INSERT INTO s23_backout_guard (typed_notification_count)
    SELECT COUNT(*)
    FROM notifications
    WHERE notification_type <> 'legacy';

DROP TABLE s23_backout_guard;

DROP INDEX IF EXISTS idx_notifications_target;
DROP INDEX IF EXISTS idx_notifications_dedupe_key;

CREATE TABLE notifications_v0005 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    body TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO notifications_v0005
    (id, user_id, title, body, is_read, created_at)
SELECT id, user_id, title, body, is_read, created_at
FROM notifications;

DROP TABLE notifications;

ALTER TABLE notifications_v0005 RENAME TO notifications;
