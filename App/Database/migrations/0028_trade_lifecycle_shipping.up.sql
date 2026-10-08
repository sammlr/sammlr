-- Finalization observation is distinct from a sender's own confirmation.
CREATE TABLE lifecycle_shipping (
 trade_id INTEGER NOT NULL,
 from_user_id INTEGER NOT NULL,
 revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
 sent_at TEXT NOT NULL,
 sender_confirmed_at TEXT,
 source TEXT NOT NULL CHECK(source IN ('SENDER_CONFIRMATION','RECEIPT_EVIDENCE')),
 actor_user_id INTEGER NOT NULL REFERENCES users(id),
 PRIMARY KEY(trade_id,from_user_id),
 FOREIGN KEY(trade_id,from_user_id) REFERENCES lifecycle_directions(trade_id,from_user_id),
 CHECK((source='SENDER_CONFIRMATION' AND sender_confirmed_at=sent_at AND actor_user_id=from_user_id)
    OR (source='RECEIPT_EVIDENCE' AND sender_confirmed_at IS NULL AND actor_user_id<>from_user_id))
);
CREATE TRIGGER lifecycle_shipping_owner BEFORE INSERT ON lifecycle_shipping
WHEN EXISTS(SELECT 1 FROM lifecycle_shipping WHERE trade_id=NEW.trade_id AND from_user_id=NEW.from_user_id)
 OR NOT EXISTS(SELECT 1 FROM lifecycle_contracts c JOIN lifecycle_directions d ON d.trade_id=c.trade_id
 WHERE c.trade_id=NEW.trade_id AND c.state='accepted' AND c.accepted_revision_id=NEW.revision_id
 AND d.from_user_id=NEW.from_user_id AND NEW.actor_user_id IN(d.from_user_id,d.to_user_id))
BEGIN SELECT RAISE(ABORT,'Invalid shipping identity'); END;
CREATE TRIGGER lifecycle_shipping_immutable BEFORE UPDATE ON lifecycle_shipping
BEGIN SELECT RAISE(ABORT,'Shipping observation is immutable'); END;
CREATE TRIGGER lifecycle_shipping_delete BEFORE DELETE ON lifecycle_shipping
BEGIN SELECT RAISE(ABORT,'Shipping cannot be undone'); END;
CREATE TRIGGER lifecycle_shipping_no_cancel BEFORE UPDATE OF state,accepted_revision_id ON lifecycle_contracts
WHEN EXISTS(SELECT 1 FROM lifecycle_shipping WHERE trade_id=OLD.trade_id)
 AND (NEW.state<>OLD.state OR NEW.accepted_revision_id<>OLD.accepted_revision_id)
BEGIN SELECT RAISE(ABORT,'Physical shipping forbids normal cancellation or amendment'); END;
CREATE TRIGGER lifecycle_shipping_no_undo BEFORE UPDATE OF shipping_state ON lifecycle_directions
WHEN EXISTS(SELECT 1 FROM lifecycle_shipping WHERE trade_id=OLD.trade_id AND from_user_id=OLD.from_user_id)
 AND NEW.shipping_state<>'sent'
BEGIN SELECT RAISE(ABORT,'Physical shipping cannot be reversed'); END;
