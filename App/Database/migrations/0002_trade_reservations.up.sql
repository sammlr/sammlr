CREATE TABLE trade_reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    trade_position_id INTEGER NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    sticker_code TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at TEXT,
    release_reason TEXT,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
    FOREIGN KEY (trade_position_id) REFERENCES trade_positions(id) ON DELETE CASCADE,
    CHECK (quantity > 0),
    CHECK (state IN ('active', 'released')),
    CHECK (
        (state = 'active' AND released_at IS NULL AND release_reason IS NULL)
        OR
        (state = 'released' AND released_at IS NOT NULL AND release_reason IS NOT NULL)
    )
);

CREATE INDEX idx_trade_reservations_active_inventory
    ON trade_reservations(user_id, album_id, sticker_code, state);

CREATE INDEX idx_trade_reservations_trade_state
    ON trade_reservations(trade_id, state);
