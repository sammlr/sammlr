-- Immutable inspection and problem evidence; direction projection stays orthogonal.
CREATE TABLE lifecycle_receipts (
 trade_id INTEGER NOT NULL,
 from_user_id INTEGER NOT NULL,
 revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
 receiver_id INTEGER NOT NULL REFERENCES users(id),
 received_at TEXT NOT NULL,
 inspection_json TEXT NOT NULL CHECK(json_valid(inspection_json)),
 has_problem INTEGER NOT NULL CHECK(has_problem IN(0,1)),
 PRIMARY KEY(trade_id,from_user_id),
 FOREIGN KEY(trade_id,from_user_id) REFERENCES lifecycle_directions(trade_id,from_user_id)
);
CREATE TABLE lifecycle_delivery_problems (
 id INTEGER PRIMARY KEY,
 trade_id INTEGER NOT NULL,
 from_user_id INTEGER NOT NULL,
 revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
 kind TEXT NOT NULL CHECK(kind IN('non_arrival','inspection')),
 reported_at TEXT NOT NULL,
 UNIQUE(trade_id,from_user_id,kind),
 FOREIGN KEY(trade_id,from_user_id) REFERENCES lifecycle_directions(trade_id,from_user_id)
);
CREATE TABLE lifecycle_delivery_responses (
 problem_id INTEGER PRIMARY KEY REFERENCES lifecycle_delivery_problems(id),
 sender_id INTEGER NOT NULL REFERENCES users(id),
 response TEXT NOT NULL CHECK(response IN('acknowledge','sent_correctly')),
 responded_at TEXT NOT NULL
);
CREATE TRIGGER lifecycle_receipt_owner BEFORE INSERT ON lifecycle_receipts
WHEN EXISTS(SELECT 1 FROM lifecycle_receipts WHERE trade_id=NEW.trade_id AND from_user_id=NEW.from_user_id)
 OR NOT EXISTS(SELECT 1 FROM lifecycle_contracts c JOIN lifecycle_directions d ON d.trade_id=c.trade_id
 JOIN lifecycle_shipping s ON s.trade_id=d.trade_id AND s.from_user_id=d.from_user_id
 WHERE c.trade_id=NEW.trade_id AND c.state='accepted' AND c.accepted_revision_id=NEW.revision_id
 AND d.from_user_id=NEW.from_user_id AND d.to_user_id=NEW.receiver_id)
BEGIN SELECT RAISE(ABORT,'Invalid receipt identity'); END;
CREATE TRIGGER lifecycle_receipt_update BEFORE UPDATE ON lifecycle_receipts
BEGIN SELECT RAISE(ABORT,'Receipt is immutable'); END;
CREATE TRIGGER lifecycle_receipt_delete BEFORE DELETE ON lifecycle_receipts
BEGIN SELECT RAISE(ABORT,'Receipt cannot be undone'); END;
CREATE TRIGGER lifecycle_delivery_problem_insert BEFORE INSERT ON lifecycle_delivery_problems
WHEN EXISTS(SELECT 1 FROM lifecycle_delivery_problems WHERE id=NEW.id OR
 (trade_id=NEW.trade_id AND from_user_id=NEW.from_user_id AND kind=NEW.kind))
 OR NOT EXISTS(SELECT 1 FROM lifecycle_contracts c JOIN lifecycle_directions d ON d.trade_id=c.trade_id
 WHERE c.trade_id=NEW.trade_id AND c.state='accepted' AND c.accepted_revision_id=NEW.revision_id AND d.from_user_id=NEW.from_user_id)
BEGIN SELECT RAISE(ABORT,'Invalid delivery problem'); END;
CREATE TRIGGER lifecycle_delivery_problem_update BEFORE UPDATE ON lifecycle_delivery_problems
BEGIN SELECT RAISE(ABORT,'Problem evidence is immutable'); END;
CREATE TRIGGER lifecycle_delivery_problem_delete BEFORE DELETE ON lifecycle_delivery_problems
BEGIN SELECT RAISE(ABORT,'Problem evidence is immutable'); END;
CREATE TRIGGER lifecycle_delivery_response_insert BEFORE INSERT ON lifecycle_delivery_responses
WHEN EXISTS(SELECT 1 FROM lifecycle_delivery_responses WHERE problem_id=NEW.problem_id)
 OR NOT EXISTS(SELECT 1 FROM lifecycle_delivery_problems WHERE id=NEW.problem_id AND from_user_id=NEW.sender_id)
BEGIN SELECT RAISE(ABORT,'Invalid problem response'); END;
CREATE TRIGGER lifecycle_delivery_response_update BEFORE UPDATE ON lifecycle_delivery_responses
BEGIN SELECT RAISE(ABORT,'Response is immutable'); END;
CREATE TRIGGER lifecycle_delivery_response_delete BEFORE DELETE ON lifecycle_delivery_responses
BEGIN SELECT RAISE(ABORT,'Response is immutable'); END;
CREATE TRIGGER lifecycle_receipt_no_undo BEFORE UPDATE OF receipt_state ON lifecycle_directions
WHEN EXISTS(SELECT 1 FROM lifecycle_receipts WHERE trade_id=OLD.trade_id AND from_user_id=OLD.from_user_id)
 AND NEW.receipt_state<>(SELECT CASE has_problem WHEN 1 THEN 'received_with_problem' ELSE 'received_complete' END
 FROM lifecycle_receipts WHERE trade_id=OLD.trade_id AND from_user_id=OLD.from_user_id)
BEGIN SELECT RAISE(ABORT,'Confirmed receipt cannot be changed'); END;
CREATE TRIGGER lifecycle_receipt_event_update BEFORE UPDATE ON trade_events
WHEN OLD.event_type IN ('ReceiptComplete','ReceiptPartial','ReceiptProblemReported','NonArrivalReported','LateArrivalReported','SenderProblemResponse')
 AND EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=OLD.trade_id)
BEGIN SELECT RAISE(ABORT,'Receipt history is immutable'); END;
CREATE TRIGGER lifecycle_receipt_event_delete BEFORE DELETE ON trade_events
WHEN OLD.event_type IN ('ReceiptComplete','ReceiptPartial','ReceiptProblemReported','NonArrivalReported','LateArrivalReported','SenderProblemResponse')
 AND EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=OLD.trade_id)
BEGIN SELECT RAISE(ABORT,'Receipt history is immutable'); END;
CREATE TRIGGER lifecycle_receipt_event_replace BEFORE INSERT ON trade_events
WHEN EXISTS(SELECT 1 FROM trade_events e JOIN lifecycle_contracts c ON c.trade_id=e.trade_id
 WHERE e.id=NEW.id AND e.event_type IN ('ReceiptComplete','ReceiptPartial','ReceiptProblemReported','NonArrivalReported','LateArrivalReported','SenderProblemResponse'))
BEGIN SELECT RAISE(ABORT,'Receipt history cannot be replaced'); END;
