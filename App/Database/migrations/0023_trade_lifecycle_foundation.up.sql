-- New contract extension of the shared trade identity. No legacy backfill.
CREATE TABLE lifecycle_contracts (
    trade_id INTEGER PRIMARY KEY REFERENCES trades(id),
    contract_type TEXT NOT NULL DEFAULT 'trade_lifecycle_v1'
        CHECK (contract_type = 'trade_lifecycle_v1'),
    origin TEXT NOT NULL CHECK (origin IN ('MANUAL', 'SMARTDEAL')),
    state TEXT NOT NULL DEFAULT 'draft' CHECK (state IN ('draft', 'open', 'accepted', 'ended')),
    current_revision_id INTEGER,
    accepted_revision_id INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (trade_id, current_revision_id) REFERENCES lifecycle_revisions(trade_id, id),
    FOREIGN KEY (trade_id, accepted_revision_id) REFERENCES lifecycle_revisions(trade_id, id)
);

CREATE TABLE lifecycle_revisions (
    id INTEGER PRIMARY KEY,
    trade_id INTEGER NOT NULL REFERENCES lifecycle_contracts(trade_id),
    number INTEGER NOT NULL CHECK (typeof(number)='integer' AND number > 0),
    author_user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL CHECK (kind IN ('original', 'counter', 'reduction')),
    sealed INTEGER NOT NULL DEFAULT 0 CHECK (sealed IN (0, 1)),
    created_at TEXT NOT NULL,
    UNIQUE (trade_id, number),
    UNIQUE (trade_id, id)
);
CREATE UNIQUE INDEX lifecycle_one_original ON lifecycle_revisions(trade_id) WHERE kind='original';
CREATE UNIQUE INDEX lifecycle_one_counter ON lifecycle_revisions(trade_id) WHERE kind='counter';

CREATE TABLE lifecycle_revision_positions (
    id INTEGER PRIMARY KEY,
    revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
    from_user_id INTEGER NOT NULL REFERENCES users(id),
    to_user_id INTEGER NOT NULL REFERENCES users(id),
    album_id TEXT NOT NULL REFERENCES albums(id),
    sticker_code TEXT NOT NULL CHECK (length(sticker_code)>0),
    quantity INTEGER NOT NULL CHECK (typeof(quantity)='integer' AND quantity>0),
    CHECK (from_user_id<>to_user_id),
    UNIQUE (revision_id, from_user_id, album_id, sticker_code)
);

CREATE TABLE lifecycle_rule_snapshots (
    revision_id INTEGER PRIMARY KEY REFERENCES lifecycle_revisions(id),
    schema_version INTEGER NOT NULL CHECK (schema_version=1),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    accepted_at TEXT NOT NULL
);

CREATE TABLE lifecycle_consents (
    revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    consented_at TEXT NOT NULL,
    PRIMARY KEY (revision_id, user_id)
);

-- Authoritative target count; absent row retains the existing one-copy target.
CREATE TABLE lifecycle_need_targets (
    user_id INTEGER NOT NULL REFERENCES users(id),
    album_id TEXT NOT NULL REFERENCES albums(id),
    sticker_code TEXT NOT NULL CHECK (length(sticker_code)>0),
    quantity INTEGER NOT NULL CHECK (typeof(quantity)='integer' AND quantity>=0),
    PRIMARY KEY (user_id, album_id, sticker_code)
);

CREATE TABLE lifecycle_need_claims (
    id INTEGER PRIMARY KEY,
    revision_position_id INTEGER NOT NULL UNIQUE REFERENCES lifecycle_revision_positions(id),
    state TEXT NOT NULL CHECK (state IN ('pending', 'committed', 'released')),
    quantity INTEGER NOT NULL CHECK (typeof(quantity)='integer' AND quantity>0),
    received_quantity INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(received_quantity)='integer' AND received_quantity BETWEEN 0 AND quantity),
    created_at TEXT NOT NULL,
    released_at TEXT,
    CHECK ((state='released') = (released_at IS NOT NULL)),
    CHECK (state<>'pending' OR received_quantity=0)
);

CREATE TABLE lifecycle_directions (
    trade_id INTEGER NOT NULL REFERENCES lifecycle_contracts(trade_id),
    from_user_id INTEGER NOT NULL REFERENCES users(id),
    to_user_id INTEGER NOT NULL REFERENCES users(id),
    preparation_state TEXT NOT NULL DEFAULT 'not_started',
    shipping_state TEXT NOT NULL DEFAULT 'not_sent',
    receipt_state TEXT NOT NULL DEFAULT 'expected',
    PRIMARY KEY (trade_id, from_user_id),
    CHECK (from_user_id<>to_user_id)
);

-- Command identity is not a lifecycle transition service. Caller commits the
-- result and associated mutations in one transaction; no autonomous commits.
CREATE TABLE lifecycle_commands (
    trade_id INTEGER NOT NULL REFERENCES lifecycle_contracts(trade_id),
    actor_user_id INTEGER NOT NULL REFERENCES users(id),
    command_key TEXT NOT NULL CHECK (length(command_key)>0),
    operation TEXT NOT NULL CHECK (length(operation)>0),
    payload_digest TEXT NOT NULL CHECK (length(payload_digest)=64),
    result_json TEXT NOT NULL CHECK (json_valid(result_json)),
    created_at TEXT NOT NULL,
    PRIMARY KEY (trade_id, actor_user_id, command_key)
);

-- One logical movement identity shared by future ship/receipt evidence paths.
CREATE TABLE lifecycle_movements (
    trade_id INTEGER NOT NULL REFERENCES lifecycle_contracts(trade_id),
    from_user_id INTEGER NOT NULL REFERENCES users(id),
    album_id TEXT NOT NULL REFERENCES albums(id),
    sticker_code TEXT NOT NULL,
    movement_kind TEXT NOT NULL CHECK (movement_kind IN ('debit', 'credit')),
    movement_key TEXT NOT NULL CHECK (length(movement_key)>0),
    quantity INTEGER NOT NULL CHECK (typeof(quantity)='integer' AND quantity>0),
    history_event_key TEXT NOT NULL UNIQUE,
    PRIMARY KEY (trade_id, from_user_id, album_id, sticker_code, movement_kind, movement_key)
);

CREATE TRIGGER lifecycle_contract_insert_guard BEFORE INSERT ON lifecycle_contracts
WHEN NOT EXISTS (SELECT 1 FROM trades t WHERE t.id=NEW.trade_id
    AND t.legacy_trade_request_id IS NULL
    AND EXISTS (SELECT 1 FROM users WHERE id=t.requester_user_id)
    AND EXISTS (SELECT 1 FROM users WHERE id=t.partner_user_id))
BEGIN SELECT RAISE(ABORT, 'Lifecycle contract requires a separate valid trade identity'); END;
CREATE TRIGGER lifecycle_contract_identity BEFORE UPDATE OF trade_id, contract_type, origin, created_at ON lifecycle_contracts
BEGIN SELECT RAISE(ABORT, 'Lifecycle contract identity is immutable'); END;
CREATE TRIGGER lifecycle_contract_delete BEFORE DELETE ON lifecycle_contracts
BEGIN SELECT RAISE(ABORT, 'Lifecycle contract cannot be erased'); END;
CREATE TRIGGER lifecycle_trade_identity BEFORE UPDATE OF requester_user_id, partner_user_id, legacy_trade_request_id ON trades
WHEN EXISTS (SELECT 1 FROM lifecycle_contracts WHERE trade_id=OLD.id)
BEGIN SELECT RAISE(ABORT, 'Lifecycle participants and contract cannot change'); END;

CREATE TRIGGER lifecycle_revision_author BEFORE INSERT ON lifecycle_revisions
WHEN NOT EXISTS (SELECT 1 FROM trades WHERE id=NEW.trade_id AND NEW.author_user_id IN (requester_user_id, partner_user_id))
 OR NEW.number<>(SELECT COALESCE(MAX(number),0)+1 FROM lifecycle_revisions WHERE trade_id=NEW.trade_id)
BEGIN SELECT RAISE(ABORT, 'Invalid revision owner or sequence'); END;
CREATE TRIGGER lifecycle_revision_immutable BEFORE UPDATE ON lifecycle_revisions
WHEN OLD.sealed=1 OR NEW.trade_id<>OLD.trade_id OR NEW.id<>OLD.id OR NEW.number<>OLD.number
 OR NEW.author_user_id<>OLD.author_user_id OR NEW.kind<>OLD.kind OR NEW.created_at<>OLD.created_at
BEGIN SELECT RAISE(ABORT, 'Revision is immutable'); END;
CREATE TRIGGER lifecycle_revision_delete BEFORE DELETE ON lifecycle_revisions
BEGIN SELECT RAISE(ABORT, 'Revision history cannot be erased'); END;
CREATE TRIGGER lifecycle_position_insert BEFORE INSERT ON lifecycle_revision_positions
WHEN NOT EXISTS (SELECT 1 FROM lifecycle_revisions r JOIN trades t ON t.id=r.trade_id
 WHERE r.id=NEW.revision_id AND r.sealed=0
 AND NEW.from_user_id IN (t.requester_user_id,t.partner_user_id)
 AND NEW.to_user_id IN (t.requester_user_id,t.partner_user_id))
BEGIN SELECT RAISE(ABORT, 'Invalid revision position'); END;
CREATE TRIGGER lifecycle_position_update BEFORE UPDATE ON lifecycle_revision_positions
BEGIN SELECT RAISE(ABORT, 'Revision position is immutable'); END;
CREATE TRIGGER lifecycle_position_delete BEFORE DELETE ON lifecycle_revision_positions
BEGIN SELECT RAISE(ABORT, 'Revision position is immutable'); END;
CREATE TRIGGER lifecycle_seal_guard BEFORE UPDATE OF sealed ON lifecycle_revisions
WHEN NEW.sealed=1 AND (SELECT COUNT(DISTINCT from_user_id) FROM lifecycle_revision_positions WHERE revision_id=NEW.id)<>2
BEGIN SELECT RAISE(ABORT, 'Both revision directions required'); END;

CREATE TRIGGER lifecycle_current_guard BEFORE UPDATE OF current_revision_id ON lifecycle_contracts
WHEN NEW.current_revision_id IS NOT NULL AND NOT EXISTS
 (SELECT 1 FROM lifecycle_revisions WHERE id=NEW.current_revision_id AND trade_id=NEW.trade_id AND sealed=1)
BEGIN SELECT RAISE(ABORT, 'Current revision must be sealed and owned'); END;
CREATE TRIGGER lifecycle_accepted_guard BEFORE UPDATE OF accepted_revision_id ON lifecycle_contracts
WHEN NEW.accepted_revision_id IS NOT NULL AND (NOT EXISTS
 (SELECT 1 FROM lifecycle_revisions r JOIN lifecycle_rule_snapshots s ON s.revision_id=r.id
 WHERE r.id=NEW.accepted_revision_id AND r.trade_id=NEW.trade_id AND r.sealed=1)
 OR (SELECT COUNT(*) FROM lifecycle_consents WHERE revision_id=NEW.accepted_revision_id)<>2)
BEGIN SELECT RAISE(ABORT, 'Accepted revision requires snapshot and both consents'); END;
CREATE TRIGGER lifecycle_consent_guard BEFORE INSERT ON lifecycle_consents
WHEN NOT EXISTS (SELECT 1 FROM lifecycle_revisions r JOIN trades t ON t.id=r.trade_id
 WHERE r.id=NEW.revision_id AND r.sealed=1 AND NEW.user_id IN (t.requester_user_id,t.partner_user_id))
BEGIN SELECT RAISE(ABORT, 'Invalid revision consent'); END;
CREATE TRIGGER lifecycle_consent_update BEFORE UPDATE ON lifecycle_consents
BEGIN SELECT RAISE(ABORT, 'Consent is immutable'); END;
CREATE TRIGGER lifecycle_consent_delete BEFORE DELETE ON lifecycle_consents
BEGIN SELECT RAISE(ABORT, 'Consent is immutable'); END;
CREATE TRIGGER lifecycle_snapshot_update BEFORE UPDATE ON lifecycle_rule_snapshots
BEGIN SELECT RAISE(ABORT, 'Rule snapshot is immutable'); END;
CREATE TRIGGER lifecycle_snapshot_delete BEFORE DELETE ON lifecycle_rule_snapshots
BEGIN SELECT RAISE(ABORT, 'Rule snapshot is immutable'); END;
CREATE TRIGGER lifecycle_claim_insert BEFORE INSERT ON lifecycle_need_claims
WHEN NOT EXISTS (SELECT 1 FROM lifecycle_revision_positions p JOIN lifecycle_revisions r ON r.id=p.revision_id
 WHERE p.id=NEW.revision_position_id AND r.sealed=1 AND p.quantity=NEW.quantity
 AND (NEW.state<>'pending' OR p.to_user_id=r.author_user_id))
BEGIN SELECT RAISE(ABORT, 'Need claim must belong to the receivers revision'); END;
CREATE TRIGGER lifecycle_claim_update BEFORE UPDATE ON lifecycle_need_claims
WHEN NEW.revision_position_id<>OLD.revision_position_id OR NEW.quantity<>OLD.quantity
 OR OLD.state='released' OR NEW.received_quantity<OLD.received_quantity
 OR (OLD.state='committed' AND NEW.state='pending')
BEGIN SELECT RAISE(ABORT, 'Invalid need claim mutation'); END;
CREATE TRIGGER lifecycle_claim_delete BEFORE DELETE ON lifecycle_need_claims
BEGIN SELECT RAISE(ABORT, 'Release claims; do not erase them'); END;
CREATE TRIGGER lifecycle_direction_guard BEFORE INSERT ON lifecycle_directions
WHEN NOT EXISTS (SELECT 1 FROM trades WHERE id=NEW.trade_id
 AND NEW.from_user_id IN (requester_user_id,partner_user_id)
 AND NEW.to_user_id IN (requester_user_id,partner_user_id))
BEGIN SELECT RAISE(ABORT, 'Invalid physical direction'); END;
CREATE TRIGGER lifecycle_direction_identity BEFORE UPDATE OF trade_id,from_user_id,to_user_id ON lifecycle_directions
BEGIN SELECT RAISE(ABORT, 'Direction identity is immutable'); END;
CREATE TRIGGER lifecycle_command_guard BEFORE INSERT ON lifecycle_commands
WHEN NOT EXISTS (SELECT 1 FROM trades WHERE id=NEW.trade_id AND NEW.actor_user_id IN (requester_user_id,partner_user_id))
BEGIN SELECT RAISE(ABORT, 'Invalid command actor'); END;
CREATE TRIGGER lifecycle_command_update BEFORE UPDATE ON lifecycle_commands
BEGIN SELECT RAISE(ABORT, 'Command result is immutable'); END;
CREATE TRIGGER lifecycle_command_delete BEFORE DELETE ON lifecycle_commands
BEGIN SELECT RAISE(ABORT, 'Command result is immutable'); END;
CREATE TRIGGER lifecycle_movement_update BEFORE UPDATE ON lifecycle_movements
BEGIN SELECT RAISE(ABORT, 'Movement is immutable'); END;
CREATE TRIGGER lifecycle_movement_delete BEFORE DELETE ON lifecycle_movements
BEGIN SELECT RAISE(ABORT, 'Movement is immutable'); END;

-- Link shared physical holds to the exact immutable offer position. There is
-- still only one physical reservation table, visible to all Inventory readers.
CREATE TABLE lifecycle_supply_bindings (
    reservation_id INTEGER NOT NULL REFERENCES trade_reservations(id),
    revision_position_id INTEGER PRIMARY KEY REFERENCES lifecycle_revision_positions(id),
    is_current INTEGER NOT NULL DEFAULT 1 CHECK(is_current IN (0,1))
);
CREATE UNIQUE INDEX lifecycle_one_supply_head ON lifecycle_supply_bindings(reservation_id) WHERE is_current=1;
CREATE TRIGGER lifecycle_supply_owner BEFORE INSERT ON lifecycle_supply_bindings
WHEN NOT EXISTS (SELECT 1 FROM trade_reservations h JOIN trade_positions m ON m.id=h.trade_position_id
 JOIN lifecycle_revision_positions p ON p.id=NEW.revision_position_id
 JOIN lifecycle_revisions r ON r.id=p.revision_id
 WHERE h.id=NEW.reservation_id AND r.sealed=1 AND h.trade_id=r.trade_id
 AND m.trade_id=r.trade_id AND h.user_id=p.from_user_id AND m.from_user_id=p.from_user_id
 AND m.to_user_id=p.to_user_id AND h.album_id=p.album_id AND m.album_id=p.album_id
 AND h.sticker_code=p.sticker_code AND m.sticker_code=p.sticker_code
 AND h.quantity=p.quantity AND m.quantity=p.quantity)
BEGIN SELECT RAISE(ABORT, 'Reservation ownership mismatch'); END;
CREATE TRIGGER lifecycle_supply_update BEFORE UPDATE ON lifecycle_supply_bindings
WHEN NEW.reservation_id<>OLD.reservation_id OR NEW.revision_position_id<>OLD.revision_position_id
 OR OLD.is_current=0 OR NEW.is_current<>0
BEGIN SELECT RAISE(ABORT, 'Supply binding identity is immutable'); END;
CREATE TRIGGER lifecycle_supply_delete BEFORE DELETE ON lifecycle_supply_bindings
BEGIN SELECT RAISE(ABORT, 'Supply binding history cannot be erased'); END;
CREATE TRIGGER lifecycle_root_initial BEFORE INSERT ON lifecycle_contracts
WHEN NEW.state<>'draft' OR NEW.current_revision_id IS NOT NULL OR NEW.accepted_revision_id IS NOT NULL
 OR NOT EXISTS(SELECT 1 FROM trades WHERE id=NEW.trade_id AND lifecycle_state='foundation')
 OR EXISTS(SELECT 1 FROM trade_positions WHERE trade_id=NEW.trade_id)
BEGIN SELECT RAISE(ABORT, 'Foundation must start with a new draft identity'); END;
CREATE TRIGGER lifecycle_accepted_monotone BEFORE UPDATE OF accepted_revision_id ON lifecycle_contracts
WHEN OLD.accepted_revision_id IS NOT NULL AND
 (NEW.accepted_revision_id IS NULL OR (NEW.accepted_revision_id<>OLD.accepted_revision_id AND NOT EXISTS
   (SELECT 1 FROM lifecycle_revisions n JOIN lifecycle_revisions o ON o.id=OLD.accepted_revision_id
    WHERE n.id=NEW.accepted_revision_id AND n.kind='reduction' AND n.number>o.number)))
BEGIN SELECT RAISE(ABORT, 'Accepted history may only advance to a reduction'); END;
CREATE TRIGGER lifecycle_snapshot_sealed BEFORE INSERT ON lifecycle_rule_snapshots
WHEN NOT EXISTS(SELECT 1 FROM lifecycle_revisions WHERE id=NEW.revision_id AND sealed=1)
BEGIN SELECT RAISE(ABORT, 'Snapshot requires sealed revision'); END;
CREATE TRIGGER lifecycle_movement_owner BEFORE INSERT ON lifecycle_movements
WHEN NOT EXISTS(SELECT 1 FROM trades WHERE id=NEW.trade_id AND NEW.from_user_id IN (requester_user_id,partner_user_id))
BEGIN SELECT RAISE(ABORT, 'Invalid movement direction'); END;

CREATE TRIGGER lifecycle_shared_hold_guard BEFORE INSERT ON trade_reservations
WHEN EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=NEW.trade_id) AND
 (NOT EXISTS(SELECT 1 FROM trade_positions p WHERE p.id=NEW.trade_position_id
    AND p.trade_id=NEW.trade_id AND p.from_user_id=NEW.user_id AND p.album_id=NEW.album_id
    AND p.sticker_code=NEW.sticker_code AND p.quantity=NEW.quantity)
  OR NEW.state<>'active'
  OR NEW.quantity + COALESCE((SELECT SUM(quantity) FROM trade_reservations
        WHERE user_id=NEW.user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code AND state='active'),0)
     > MAX(COALESCE((SELECT SUM(quantity) FROM stickers WHERE user_id=NEW.user_id
        AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code),0)-1,0))
BEGIN SELECT RAISE(ABORT, 'Invalid or overdrawn shared lifecycle reservation'); END;
CREATE TRIGGER lifecycle_shared_hold_identity BEFORE UPDATE ON trade_reservations
WHEN EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=OLD.trade_id) AND
 (NEW.id<>OLD.id OR NEW.trade_id<>OLD.trade_id OR NEW.trade_position_id<>OLD.trade_position_id
 OR NEW.user_id<>OLD.user_id OR NEW.album_id<>OLD.album_id OR NEW.sticker_code<>OLD.sticker_code
 OR NEW.created_at<>OLD.created_at OR (NEW.quantity<>OLD.quantity AND OLD.state='active'))
BEGIN SELECT RAISE(ABORT, 'Lifecycle hold identity cannot change or reactivate'); END;

CREATE TRIGGER lifecycle_contracts_no_replace BEFORE INSERT ON lifecycle_contracts
WHEN EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=NEW.trade_id)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_revisions_no_replace BEFORE INSERT ON lifecycle_revisions
WHEN EXISTS(SELECT 1 FROM lifecycle_revisions WHERE id=NEW.id)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_revision_positions_no_replace BEFORE INSERT ON lifecycle_revision_positions
WHEN EXISTS(SELECT 1 FROM lifecycle_revision_positions WHERE id=NEW.id)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_rule_snapshots_no_replace BEFORE INSERT ON lifecycle_rule_snapshots
WHEN EXISTS(SELECT 1 FROM lifecycle_rule_snapshots WHERE revision_id=NEW.revision_id)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_consents_no_replace BEFORE INSERT ON lifecycle_consents
WHEN EXISTS(SELECT 1 FROM lifecycle_consents WHERE revision_id=NEW.revision_id AND user_id=NEW.user_id)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_need_claims_no_replace BEFORE INSERT ON lifecycle_need_claims
WHEN EXISTS(SELECT 1 FROM lifecycle_need_claims WHERE revision_position_id=NEW.revision_position_id)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_directions_no_replace BEFORE INSERT ON lifecycle_directions
WHEN EXISTS(SELECT 1 FROM lifecycle_directions WHERE trade_id=NEW.trade_id AND from_user_id=NEW.from_user_id)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_commands_no_replace BEFORE INSERT ON lifecycle_commands
WHEN EXISTS(SELECT 1 FROM lifecycle_commands WHERE trade_id=NEW.trade_id AND actor_user_id=NEW.actor_user_id AND command_key=NEW.command_key)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_movements_no_replace BEFORE INSERT ON lifecycle_movements
WHEN EXISTS(SELECT 1 FROM lifecycle_movements WHERE trade_id=NEW.trade_id AND from_user_id=NEW.from_user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code AND movement_kind=NEW.movement_kind AND movement_key=NEW.movement_key)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_supply_bindings_no_replace BEFORE INSERT ON lifecycle_supply_bindings
WHEN EXISTS(SELECT 1 FROM lifecycle_supply_bindings WHERE revision_position_id=NEW.revision_position_id)
BEGIN SELECT RAISE(ABORT, 'Immutable lifecycle identity already exists'); END;

CREATE TRIGGER lifecycle_movement_event_no_replace BEFORE INSERT ON lifecycle_movements
WHEN EXISTS(SELECT 1 FROM lifecycle_movements WHERE history_event_key=NEW.history_event_key)
BEGIN SELECT RAISE(ABORT, 'Movement event already exists'); END;

-- Shared rows are the current physical projection, not revision history.
-- A released hold may be rebound to a new immutable revision. Recheck supply
-- on reactivation; active quantity/ownership cannot be silently rewritten.
CREATE TRIGGER lifecycle_shared_rebind_guard BEFORE UPDATE ON trade_reservations
WHEN EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=OLD.trade_id)
 AND NEW.state='active' AND OLD.state='released' AND
 (NOT EXISTS(SELECT 1 FROM trade_positions p WHERE p.id=NEW.trade_position_id AND p.quantity=NEW.quantity)
 OR NEW.quantity+COALESCE((SELECT SUM(quantity) FROM trade_reservations
     WHERE id<>OLD.id AND user_id=NEW.user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code AND state='active'),0)
    > MAX(COALESCE((SELECT SUM(quantity) FROM stickers WHERE user_id=NEW.user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code),0)-1,0))
BEGIN SELECT RAISE(ABORT, 'Insufficient shared supply for rebind'); END;
CREATE TRIGGER lifecycle_materialized_position_insert BEFORE INSERT ON trade_positions
WHEN EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=NEW.trade_id) AND
 (typeof(NEW.quantity)<>'integer' OR NOT EXISTS(SELECT 1 FROM trades t WHERE t.id=NEW.trade_id
   AND NEW.from_user_id IN (t.requester_user_id,t.partner_user_id) AND NEW.to_user_id IN (t.requester_user_id,t.partner_user_id)))
BEGIN SELECT RAISE(ABORT, 'Invalid materialized lifecycle direction'); END;
CREATE TRIGGER lifecycle_materialized_position_update BEFORE UPDATE ON trade_positions
WHEN EXISTS(SELECT 1 FROM lifecycle_contracts WHERE trade_id=OLD.trade_id) AND
 (NEW.id<>OLD.id OR NEW.trade_id<>OLD.trade_id OR NEW.from_user_id<>OLD.from_user_id OR NEW.to_user_id<>OLD.to_user_id
 OR NEW.album_id<>OLD.album_id OR NEW.sticker_code<>OLD.sticker_code OR typeof(NEW.quantity)<>'integer'
 OR EXISTS(SELECT 1 FROM trade_reservations WHERE trade_position_id=OLD.id AND state='active'))
BEGIN SELECT RAISE(ABORT, 'Release before changing physical projection; identity stays fixed'); END;
CREATE TRIGGER lifecycle_revision_kind_no_replace BEFORE INSERT ON lifecycle_revisions
WHEN NEW.kind IN ('original','counter') AND EXISTS
 (SELECT 1 FROM lifecycle_revisions WHERE trade_id=NEW.trade_id AND kind=NEW.kind)
BEGIN SELECT RAISE(ABORT, 'Original and counter history cannot be replaced'); END;
CREATE TRIGGER lifecycle_position_key_no_replace BEFORE INSERT ON lifecycle_revision_positions
WHEN EXISTS(SELECT 1 FROM lifecycle_revision_positions WHERE revision_id=NEW.revision_id
 AND from_user_id=NEW.from_user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code)
BEGIN SELECT RAISE(ABORT, 'Revision position already exists'); END;
CREATE TRIGGER lifecycle_claim_id_no_replace BEFORE INSERT ON lifecycle_need_claims
WHEN EXISTS(SELECT 1 FROM lifecycle_need_claims WHERE id=NEW.id)
BEGIN SELECT RAISE(ABORT, 'Claim identity already exists'); END;
CREATE TRIGGER lifecycle_supply_head_no_replace BEFORE INSERT ON lifecycle_supply_bindings
WHEN NEW.is_current=1 AND EXISTS(SELECT 1 FROM lifecycle_supply_bindings WHERE reservation_id=NEW.reservation_id AND is_current=1)
BEGIN SELECT RAISE(ABORT, 'Retire the prior supply head explicitly'); END;
