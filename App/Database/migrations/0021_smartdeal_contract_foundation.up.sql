-- Explicit opt-in for future V1 writers; all existing/omitted values stay legacy.
ALTER TABLE trade_requests ADD COLUMN contract_type TEXT NOT NULL DEFAULT 'legacy'
    CHECK (contract_type IN ('legacy', 'smartdeal_v1'));
-- Storage only: no default clock, reservation, acceptance or legacy backfill.
ALTER TABLE trade_requests ADD COLUMN binding_created_at TEXT;
ALTER TABLE trade_requests ADD COLUMN accepted_at TEXT;

CREATE TRIGGER trade_request_contract_type_immutable
BEFORE UPDATE OF contract_type ON trade_requests
WHEN NEW.contract_type IS NOT OLD.contract_type
BEGIN
    SELECT RAISE(ABORT, 'Request contract type is immutable');
END;

CREATE TRIGGER trade_request_binding_time_immutable
BEFORE UPDATE OF binding_created_at ON trade_requests
WHEN OLD.binding_created_at IS NOT NULL
    AND NEW.binding_created_at IS NOT OLD.binding_created_at
BEGIN
    SELECT RAISE(ABORT, 'Request binding time is immutable');
END;

CREATE TRIGGER trade_request_acceptance_time_immutable
BEFORE UPDATE OF accepted_at ON trade_requests
WHEN OLD.accepted_at IS NOT NULL AND NEW.accepted_at IS NOT OLD.accepted_at
BEGIN
    SELECT RAISE(ABORT, 'Request acceptance time is immutable');
END;
