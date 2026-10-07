CREATE TEMP TABLE lifecycle_requests_rollback_guard (empty INTEGER CHECK(empty=0));
INSERT INTO lifecycle_requests_rollback_guard SELECT COUNT(*) FROM lifecycle_requests;
DROP TABLE lifecycle_requests_rollback_guard;
DROP TRIGGER lifecycle_request_delete;
DROP TRIGGER lifecycle_request_update;
DROP TRIGGER lifecycle_request_insert;
DROP TABLE lifecycle_requests;
