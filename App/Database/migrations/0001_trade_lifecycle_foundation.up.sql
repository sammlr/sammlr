CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_trade_request_id INTEGER UNIQUE,
    requester_user_id INTEGER NOT NULL,
    partner_user_id INTEGER NOT NULL,
    lifecycle_state TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    CHECK (requester_user_id <> partner_user_id)
);

CREATE TABLE trade_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    from_user_id INTEGER NOT NULL,
    to_user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    sticker_code TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
    CHECK (from_user_id <> to_user_id),
    CHECK (quantity > 0),
    UNIQUE (trade_id, from_user_id, to_user_id, album_id, sticker_code)
);

CREATE INDEX idx_trade_positions_trade_id
    ON trade_positions(trade_id);

CREATE TABLE trade_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor_user_id INTEGER,
    payload_json TEXT,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
);

CREATE INDEX idx_trade_events_trade_time
    ON trade_events(trade_id, occurred_at, id);
