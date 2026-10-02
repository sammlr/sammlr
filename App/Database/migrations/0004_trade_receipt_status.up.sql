CREATE TABLE trade_receipt_status (
    trade_id INTEGER PRIMARY KEY,
    requester_received INTEGER NOT NULL DEFAULT 0,
    requester_received_at TEXT,
    partner_received INTEGER NOT NULL DEFAULT 0,
    partner_received_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
    CHECK (requester_received IN (0, 1)),
    CHECK (partner_received IN (0, 1)),
    CHECK (
        (requester_received = 0 AND requester_received_at IS NULL)
        OR
        (requester_received = 1 AND requester_received_at IS NOT NULL)
    ),
    CHECK (
        (partner_received = 0 AND partner_received_at IS NULL)
        OR
        (partner_received = 1 AND partner_received_at IS NOT NULL)
    )
);

INSERT INTO trade_receipt_status (trade_id)
    SELECT id FROM trades
    WHERE lifecycle_state IN (
        'accepted', 'partially_shipped', 'shipped', 'partially_received'
    );
