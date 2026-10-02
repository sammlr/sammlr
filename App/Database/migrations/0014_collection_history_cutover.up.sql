CREATE TABLE historical_inventory_mutations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL UNIQUE,
    user_album_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    sticker_code TEXT NOT NULL,
    source_type TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    requested_value INTEGER NOT NULL,
    previous_quantity INTEGER NOT NULL,
    result_quantity INTEGER NOT NULL,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_album_id, user_id, album_id)
        REFERENCES user_albums(id, user_id, album_id) ON DELETE RESTRICT,
    CHECK (length(trim(event_key)) > 0),
    CHECK (length(trim(sticker_code)) > 0),
    CHECK (source_type IN (
        'inventory', 'paper_trade', 'trade_receipt', 'trade_shipping'
    )),
    CHECK (operation_type IN ('delta', 'set')),
    CHECK (
        operation_type = 'delta'
        OR requested_value >= 0
    ),
    CHECK (previous_quantity >= 0),
    CHECK (result_quantity >= 0),
    CHECK (length(trim(occurred_at)) > 0)
);

CREATE INDEX idx_cb002_inventory_mutations_album_time
    ON historical_inventory_mutations(user_album_id, occurred_at, id);
