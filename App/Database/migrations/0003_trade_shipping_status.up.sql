CREATE TABLE trade_shipping_status (
    trade_id INTEGER PRIMARY KEY,
    requester_shipped INTEGER NOT NULL DEFAULT 0,
    requester_shipped_at TEXT,
    partner_shipped INTEGER NOT NULL DEFAULT 0,
    partner_shipped_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
    CHECK (requester_shipped IN (0, 1)),
    CHECK (partner_shipped IN (0, 1)),
    CHECK (
        (requester_shipped = 0 AND requester_shipped_at IS NULL)
        OR
        (requester_shipped = 1 AND requester_shipped_at IS NOT NULL)
    ),
    CHECK (
        (partner_shipped = 0 AND partner_shipped_at IS NULL)
        OR
        (partner_shipped = 1 AND partner_shipped_at IS NOT NULL)
    )
);

INSERT INTO trade_shipping_status (trade_id)
    SELECT id FROM trades
    WHERE lifecycle_state IN ('accepted', 'partially_shipped', 'shipped');
