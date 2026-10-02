CREATE TEMP TABLE s17_backout_guard (
    report_count INTEGER NOT NULL CHECK (report_count = 0)
);
INSERT INTO s17_backout_guard (report_count)
    SELECT COUNT(*) FROM trade_receipt_reports;
DROP TABLE s17_backout_guard;

DROP INDEX IF EXISTS idx_trade_receipt_report_positions_trade_position;
DROP TABLE IF EXISTS trade_receipt_report_positions;
DROP INDEX IF EXISTS idx_trade_receipt_reports_trade_state;
DROP TABLE IF EXISTS trade_receipt_reports;
