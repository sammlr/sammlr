-- Isolated V1 preparation and privately served control packages.
CREATE TABLE lifecycle_preparation_cycles (
 id INTEGER PRIMARY KEY,
 trade_id INTEGER NOT NULL REFERENCES lifecycle_contracts(trade_id),
 revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
 owner_id INTEGER NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 completed_at TEXT,
 revealed_at TEXT,
 review_state TEXT NOT NULL DEFAULT 'pending' CHECK(review_state IN ('pending','approved','problem')),
 is_current INTEGER NOT NULL DEFAULT 1 CHECK(is_current IN (0,1))
);
CREATE UNIQUE INDEX lifecycle_current_preparation ON lifecycle_preparation_cycles(trade_id,owner_id) WHERE is_current=1;
CREATE TABLE lifecycle_control_photos (
 id INTEGER PRIMARY KEY,
 cycle_id INTEGER NOT NULL REFERENCES lifecycle_preparation_cycles(id),
 storage_name TEXT NOT NULL UNIQUE,
 mime TEXT NOT NULL,
 digest TEXT NOT NULL,
 created_at TEXT NOT NULL,
 removed_at TEXT
);
CREATE TABLE lifecycle_photo_problems (
 id INTEGER PRIMARY KEY,
 cycle_id INTEGER NOT NULL REFERENCES lifecycle_preparation_cycles(id),
 reporter_id INTEGER NOT NULL REFERENCES users(id),
 reason TEXT NOT NULL CHECK(reason IN ('MISSING_STICKER','WRONG_STICKER','CONDITION_PROBLEM','NOT_RECOGNIZABLE')),
 position_id INTEGER REFERENCES lifecycle_revision_positions(id),
 quantity INTEGER CHECK(quantity IS NULL OR (typeof(quantity)='integer' AND quantity>0)),
 created_at TEXT NOT NULL,
 resolved_at TEXT
);
CREATE TABLE lifecycle_reductions (
 revision_id INTEGER PRIMARY KEY REFERENCES lifecycle_revisions(id),
 trade_id INTEGER NOT NULL REFERENCES lifecycle_contracts(trade_id),
 base_revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
 proposer_id INTEGER NOT NULL REFERENCES users(id),
 state TEXT NOT NULL DEFAULT 'proposed' CHECK(state IN ('proposed','approved','rejected')),
 created_at TEXT NOT NULL,
 decided_at TEXT
);
CREATE UNIQUE INDEX lifecycle_one_open_reduction ON lifecycle_reductions(trade_id) WHERE state='proposed';
CREATE TABLE physical_missing_holds (
 id INTEGER PRIMARY KEY,
 reservation_id INTEGER NOT NULL REFERENCES trade_reservations(id),
 position_id INTEGER NOT NULL REFERENCES lifecycle_revision_positions(id),
 user_id INTEGER NOT NULL REFERENCES users(id),
 album_id TEXT NOT NULL REFERENCES albums(id),
 sticker_code TEXT NOT NULL,
 quantity INTEGER NOT NULL CHECK(typeof(quantity)='integer' AND quantity>0),
 overlap_quantity INTEGER NOT NULL CHECK(typeof(overlap_quantity)='integer' AND overlap_quantity BETWEEN 0 AND quantity),
 created_at TEXT NOT NULL,
 resolved_at TEXT,
 resolution TEXT CHECK(resolution IN ('found','corrected')),
 CHECK((resolved_at IS NULL)=(resolution IS NULL))
);
CREATE UNIQUE INDEX physical_missing_active_position ON physical_missing_holds(position_id) WHERE resolved_at IS NULL;
CREATE TRIGGER physical_missing_owner BEFORE INSERT ON physical_missing_holds
WHEN NOT EXISTS(SELECT 1 FROM trade_reservations h JOIN lifecycle_contracts c ON c.trade_id=h.trade_id
 WHERE h.id=NEW.reservation_id AND h.user_id=NEW.user_id AND h.album_id=NEW.album_id
 AND h.sticker_code=NEW.sticker_code AND h.state='active' AND NEW.quantity<=h.quantity
 AND NEW.overlap_quantity=NEW.quantity AND c.state='accepted'
 AND EXISTS(SELECT 1 FROM lifecycle_supply_bindings b WHERE b.reservation_id=h.id AND b.revision_position_id=NEW.position_id AND b.is_current=1)
 AND NEW.quantity+COALESCE((SELECT SUM(overlap_quantity) FROM physical_missing_holds WHERE reservation_id=h.id AND resolved_at IS NULL),0)<=h.quantity)
BEGIN SELECT RAISE(ABORT,'Invalid physical missing declaration'); END;
CREATE TRIGGER physical_missing_identity BEFORE UPDATE ON physical_missing_holds
WHEN NEW.id<>OLD.id OR NEW.reservation_id<>OLD.reservation_id OR NEW.user_id<>OLD.user_id
 OR NEW.album_id<>OLD.album_id OR NEW.sticker_code<>OLD.sticker_code OR NEW.created_at<>OLD.created_at
 OR NEW.position_id<>OLD.position_id OR NEW.quantity<OLD.quantity OR OLD.resolved_at IS NOT NULL
 OR NEW.overlap_quantity>OLD.overlap_quantity+(NEW.quantity-OLD.quantity)
 OR (NEW.quantity>OLD.quantity AND NOT EXISTS(SELECT 1 FROM trade_reservations h
    JOIN lifecycle_supply_bindings b ON b.reservation_id=h.id AND b.is_current=1
    WHERE h.id=NEW.reservation_id AND h.state='active' AND b.revision_position_id=NEW.position_id
    AND NEW.overlap_quantity+COALESCE((SELECT SUM(overlap_quantity) FROM physical_missing_holds WHERE reservation_id=h.id AND resolved_at IS NULL AND id<>OLD.id),0)<=h.quantity))
BEGIN SELECT RAISE(ABORT,'Immutable missing-hold identity'); END;
CREATE TRIGGER physical_missing_delete BEFORE DELETE ON physical_missing_holds
BEGIN SELECT RAISE(ABORT,'Resolve missing holds explicitly'); END;
-- The overlap belongs to this concrete held quantity, never an unrelated trade.
CREATE TRIGGER physical_missing_release_overlap AFTER UPDATE OF state ON trade_reservations
WHEN NEW.state<>'active' AND OLD.state='active'
BEGIN UPDATE physical_missing_holds SET overlap_quantity=0 WHERE reservation_id=OLD.id AND resolved_at IS NULL; END;
CREATE TRIGGER lifecycle_preparation_owner BEFORE INSERT ON lifecycle_preparation_cycles
WHEN NOT EXISTS(SELECT 1 FROM lifecycle_contracts c JOIN trades t ON t.id=c.trade_id
 WHERE c.trade_id=NEW.trade_id AND c.state='accepted' AND c.accepted_revision_id=NEW.revision_id
 AND NEW.owner_id IN (t.requester_user_id,t.partner_user_id))
BEGIN SELECT RAISE(ABORT,'Invalid preparation owner or revision'); END;
CREATE TRIGGER lifecycle_photo_frozen BEFORE INSERT ON lifecycle_control_photos
WHEN NOT EXISTS(SELECT 1 FROM lifecycle_preparation_cycles WHERE id=NEW.cycle_id AND is_current=1 AND completed_at IS NULL)
BEGIN SELECT RAISE(ABORT,'Photo package frozen'); END;
-- Every reservation consumer observes quarantined free supply, including legacy
-- consumers. Existing contracts/states are not migrated or released.
CREATE TRIGGER physical_missing_reservation_insert BEFORE INSERT ON trade_reservations
WHEN NEW.state='active' AND EXISTS(SELECT 1 FROM physical_missing_holds WHERE user_id=NEW.user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code AND resolved_at IS NULL)
 AND NEW.quantity + COALESCE((SELECT SUM(quantity) FROM trade_reservations WHERE user_id=NEW.user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code AND state='active'),0)
 + COALESCE((SELECT SUM(m.quantity-CASE WHEN h.state='active' THEN m.overlap_quantity ELSE 0 END) FROM physical_missing_holds m JOIN trade_reservations h ON h.id=m.reservation_id WHERE m.user_id=NEW.user_id AND m.album_id=NEW.album_id AND m.sticker_code=NEW.sticker_code AND m.resolved_at IS NULL),0)
 > MAX(COALESCE((SELECT quantity FROM stickers WHERE user_id=NEW.user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code),0)-1,0)
BEGIN SELECT RAISE(ABORT,'Physically missing supply is not reservable'); END;
CREATE TRIGGER physical_missing_reservation_rebind BEFORE UPDATE ON trade_reservations
WHEN NEW.state='active' AND (OLD.state<>'active' OR NEW.quantity>OLD.quantity)
 AND EXISTS(SELECT 1 FROM physical_missing_holds WHERE user_id=NEW.user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code AND resolved_at IS NULL)
 AND NEW.quantity + COALESCE((SELECT SUM(quantity) FROM trade_reservations WHERE id<>OLD.id AND user_id=NEW.user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code AND state='active'),0)
 + COALESCE((SELECT SUM(m.quantity-CASE WHEN h.state='active' THEN m.overlap_quantity ELSE 0 END) FROM physical_missing_holds m JOIN trade_reservations h ON h.id=m.reservation_id WHERE m.user_id=NEW.user_id AND m.album_id=NEW.album_id AND m.sticker_code=NEW.sticker_code AND m.resolved_at IS NULL),0)
 > MAX(COALESCE((SELECT quantity FROM stickers WHERE user_id=NEW.user_id AND album_id=NEW.album_id AND sticker_code=NEW.sticker_code),0)-1,0)
BEGIN SELECT RAISE(ABORT,'Physically missing supply is not reservable'); END;
