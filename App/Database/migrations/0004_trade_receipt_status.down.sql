CREATE TEMP TABLE s16_backout_guard (
    received_count INTEGER NOT NULL CHECK (received_count = 0)
);
INSERT INTO s16_backout_guard (received_count)
    SELECT COUNT(*) FROM trade_receipt_status
    WHERE requester_received = 1 OR partner_received = 1;
DROP TABLE s16_backout_guard;

DROP TABLE IF EXISTS trade_receipt_status;
