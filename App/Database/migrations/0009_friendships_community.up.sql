CREATE TABLE friendship_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_user_id INTEGER NOT NULL,
    recipient_user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'declined', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (requester_user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (recipient_user_id) REFERENCES users(id) ON DELETE RESTRICT,
    CHECK (requester_user_id <> recipient_user_id)
);

CREATE UNIQUE INDEX idx_friendship_requests_pending_direction
    ON friendship_requests(requester_user_id, recipient_user_id)
    WHERE status='pending';
CREATE INDEX idx_friendship_requests_recipient_status
    ON friendship_requests(recipient_user_id, status, created_at, id);

CREATE TABLE friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_low_id INTEGER NOT NULL,
    user_high_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'accepted' CHECK (status='accepted'),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_low_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_high_id) REFERENCES users(id) ON DELETE RESTRICT,
    CHECK (user_low_id < user_high_id),
    UNIQUE (user_low_id, user_high_id)
);

CREATE INDEX idx_friendships_high_user
    ON friendships(user_high_id, user_low_id);

CREATE TABLE blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocker_user_id INTEGER NOT NULL,
    blocked_user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blocker_user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (blocked_user_id) REFERENCES users(id) ON DELETE RESTRICT,
    CHECK (blocker_user_id <> blocked_user_id),
    UNIQUE (blocker_user_id, blocked_user_id)
);

CREATE INDEX idx_blocks_blocked_user
    ON blocks(blocked_user_id, blocker_user_id);

CREATE TABLE user_activity (
    user_id INTEGER PRIMARY KEY,
    last_active_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);
