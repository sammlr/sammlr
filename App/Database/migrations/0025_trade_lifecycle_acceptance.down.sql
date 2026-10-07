-- Conservatively refuse downgrade once request/acceptance history exists.
CREATE TEMP TABLE lifecycle_acceptance_rollback_guard (empty INTEGER CHECK(empty=0));
INSERT INTO lifecycle_acceptance_rollback_guard SELECT COUNT(*) FROM lifecycle_requests;
INSERT INTO lifecycle_acceptance_rollback_guard SELECT COUNT(*) FROM lifecycle_acceptances;
DROP TABLE lifecycle_acceptance_rollback_guard;
DROP TRIGGER lifecycle_acceptance_insert;
DROP TRIGGER lifecycle_acceptance_update;
DROP TRIGGER lifecycle_acceptance_delete;
DROP TABLE lifecycle_acceptances;
DROP TRIGGER lifecycle_request_insert;
DROP TRIGGER lifecycle_request_update;
DROP TRIGGER lifecycle_request_delete;
DROP TABLE lifecycle_requests;
-- Request metadata is separate from immutable revisions and legacy requests.
CREATE TABLE lifecycle_requests (
    trade_id INTEGER PRIMARY KEY REFERENCES lifecycle_contracts(trade_id),
    revision_id INTEGER NOT NULL UNIQUE REFERENCES lifecycle_revisions(id),
    sender_user_id INTEGER NOT NULL REFERENCES users(id),
    command_key TEXT NOT NULL CHECK(length(command_key) BETWEEN 1 AND 200),
    payload_digest TEXT NOT NULL CHECK(length(payload_digest)=64),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','withdrawn','rejected','expired')),
    ended_at TEXT,
    UNIQUE(sender_user_id,command_key),
    CHECK((status='open')=(ended_at IS NULL)),
    CHECK(julianday(expires_at) IS NOT NULL AND julianday(created_at) IS NOT NULL
          AND abs(julianday(expires_at)-julianday(created_at)-3)<0.00000001)
);
CREATE INDEX lifecycle_requests_expiry ON lifecycle_requests(status,expires_at);
CREATE TRIGGER lifecycle_request_insert BEFORE INSERT ON lifecycle_requests BEGIN
    SELECT CASE WHEN EXISTS(SELECT 1 FROM lifecycle_requests WHERE trade_id=NEW.trade_id OR
        (sender_user_id=NEW.sender_user_id AND command_key=NEW.command_key))
        THEN RAISE(ABORT,'Immutable request identity') END;
    SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lifecycle_contracts c
        JOIN trades t ON t.id=c.trade_id JOIN lifecycle_revisions r ON r.id=NEW.revision_id
        WHERE c.trade_id=NEW.trade_id AND c.state='open' AND c.accepted_revision_id IS NULL
          AND c.current_revision_id=r.id AND r.trade_id=c.trade_id AND r.kind='original' AND r.sealed=1
          AND r.author_user_id=NEW.sender_user_id AND t.requester_user_id=NEW.sender_user_id)
        OR NEW.status<>'open' THEN RAISE(ABORT,'Invalid request ownership') END;
END;
CREATE TRIGGER lifecycle_request_update BEFORE UPDATE ON lifecycle_requests BEGIN
    SELECT CASE WHEN NEW.trade_id<>OLD.trade_id OR NEW.revision_id<>OLD.revision_id
      OR NEW.sender_user_id<>OLD.sender_user_id OR NEW.command_key<>OLD.command_key
      OR NEW.payload_digest<>OLD.payload_digest OR NEW.created_at<>OLD.created_at OR NEW.expires_at<>OLD.expires_at
      OR OLD.status<>'open' OR NEW.status='open'
      THEN RAISE(ABORT,'Immutable request or terminal state') END;
END;
CREATE TRIGGER lifecycle_request_delete BEFORE DELETE ON lifecycle_requests BEGIN
    SELECT RAISE(ABORT,'Request history cannot be deleted');
END;
