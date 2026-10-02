ALTER TABLE notifications
    ADD COLUMN notification_type TEXT NOT NULL DEFAULT 'legacy';

ALTER TABLE notifications
    ADD COLUMN target_type TEXT;

ALTER TABLE notifications
    ADD COLUMN target_id INTEGER;

ALTER TABLE notifications
    ADD COLUMN source_event_id INTEGER;

ALTER TABLE notifications
    ADD COLUMN dedupe_key TEXT;

CREATE UNIQUE INDEX idx_notifications_dedupe_key
    ON notifications(dedupe_key)
    WHERE dedupe_key IS NOT NULL;

CREATE INDEX idx_notifications_target
    ON notifications(target_type, target_id);
