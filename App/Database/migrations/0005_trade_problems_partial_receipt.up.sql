CREATE TABLE trade_receipt_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    receiver_user_id INTEGER NOT NULL,
    receiver_side TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'open',
    shipment_lost INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
    UNIQUE (trade_id, receiver_user_id),
    CHECK (receiver_side IN ('requester', 'partner')),
    CHECK (state IN ('open', 'resolved')),
    CHECK (shipment_lost IN (0, 1)),
    CHECK (
        (state = 'open' AND resolved_at IS NULL)
        OR
        (state = 'resolved' AND resolved_at IS NOT NULL)
    )
);

CREATE INDEX idx_trade_receipt_reports_trade_state
    ON trade_receipt_reports(trade_id, state);

CREATE TABLE trade_receipt_report_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    trade_position_id INTEGER NOT NULL,
    expected_quantity INTEGER NOT NULL,
    initial_received_quantity INTEGER NOT NULL,
    resolution_received_quantity INTEGER NOT NULL DEFAULT 0,
    problem_type TEXT,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY (report_id) REFERENCES trade_receipt_reports(id) ON DELETE CASCADE,
    FOREIGN KEY (trade_position_id) REFERENCES trade_positions(id) ON DELETE CASCADE,
    UNIQUE (report_id, trade_position_id),
    CHECK (expected_quantity > 0),
    CHECK (initial_received_quantity >= 0),
    CHECK (initial_received_quantity <= expected_quantity),
    CHECK (resolution_received_quantity >= 0),
    CHECK (
        initial_received_quantity + resolution_received_quantity
        <= expected_quantity
    ),
    CHECK (
        problem_type IS NULL
        OR problem_type IN (
            'missing', 'wrong_sticker', 'damaged', 'shipment_lost'
        )
    ),
    CHECK (state IN ('fulfilled', 'open', 'resolved')),
    CHECK (
        (state = 'fulfilled'
         AND initial_received_quantity = expected_quantity
         AND resolution_received_quantity = 0
         AND problem_type IS NULL
         AND resolved_at IS NULL)
        OR
        (state = 'open'
         AND initial_received_quantity < expected_quantity
         AND resolution_received_quantity = 0
         AND problem_type IS NOT NULL
         AND resolved_at IS NULL)
        OR
        (state = 'resolved'
         AND initial_received_quantity < expected_quantity
         AND initial_received_quantity + resolution_received_quantity
             = expected_quantity
         AND problem_type IS NOT NULL
         AND resolved_at IS NOT NULL)
    )
);

CREATE INDEX idx_trade_receipt_report_positions_trade_position
    ON trade_receipt_report_positions(trade_position_id, state);
