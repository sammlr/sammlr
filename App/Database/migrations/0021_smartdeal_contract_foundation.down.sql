-- Do not silently turn persisted V1 contracts back into legacy contracts.
CREATE TEMP TABLE smartdeal_contract_backout_guard (
    safe INTEGER NOT NULL CHECK (safe = 1)
);
INSERT INTO smartdeal_contract_backout_guard (safe)
SELECT CASE WHEN EXISTS (
    SELECT 1 FROM trade_requests
    WHERE contract_type <> 'legacy'
        OR binding_created_at IS NOT NULL OR accepted_at IS NOT NULL
) THEN 0 ELSE 1 END;
DROP TABLE smartdeal_contract_backout_guard;

DROP TRIGGER trade_request_acceptance_time_immutable;
DROP TRIGGER trade_request_binding_time_immutable;
DROP TRIGGER trade_request_contract_type_immutable;
ALTER TABLE trade_requests DROP COLUMN accepted_at;
ALTER TABLE trade_requests DROP COLUMN binding_created_at;
ALTER TABLE trade_requests DROP COLUMN contract_type;
