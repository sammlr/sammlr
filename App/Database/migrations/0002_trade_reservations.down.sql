CREATE TEMP TABLE s14_backout_guard (
    reservation_count INTEGER NOT NULL CHECK (reservation_count = 0)
);
INSERT INTO s14_backout_guard (reservation_count)
    SELECT COUNT(*) FROM trade_reservations;
DROP TABLE s14_backout_guard;

DROP INDEX IF EXISTS idx_trade_reservations_trade_state;
DROP INDEX IF EXISTS idx_trade_reservations_active_inventory;
DROP TABLE IF EXISTS trade_reservations;
