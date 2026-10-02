CREATE TEMP TABLE s29_backout_guard (
    persisted_count INTEGER NOT NULL CHECK (persisted_count = 0)
);

INSERT INTO s29_backout_guard (persisted_count)
SELECT
    (SELECT COUNT(*) FROM friendship_requests) +
    (SELECT COUNT(*) FROM friendships) +
    (SELECT COUNT(*) FROM blocks) +
    (SELECT COUNT(*) FROM user_activity) +
    (SELECT COUNT(*) FROM notifications
       WHERE notification_type IN ('friend_request', 'friend_accepted'));

DROP TABLE s29_backout_guard;

DROP INDEX IF EXISTS idx_blocks_blocked_user;
DROP TABLE blocks;
DROP INDEX IF EXISTS idx_friendships_high_user;
DROP TABLE friendships;
DROP INDEX IF EXISTS idx_friendship_requests_recipient_status;
DROP INDEX IF EXISTS idx_friendship_requests_pending_direction;
DROP TABLE friendship_requests;
DROP TABLE user_activity;
