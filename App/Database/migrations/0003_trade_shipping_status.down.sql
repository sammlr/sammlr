CREATE TEMP TABLE s15_backout_guard (
    shipped_count INTEGER NOT NULL CHECK (shipped_count = 0)
);
INSERT INTO s15_backout_guard (shipped_count)
    SELECT COUNT(*) FROM trade_shipping_status
    WHERE requester_shipped = 1 OR partner_shipped = 1;
DROP TABLE s15_backout_guard;

DROP TABLE IF EXISTS trade_shipping_status;
