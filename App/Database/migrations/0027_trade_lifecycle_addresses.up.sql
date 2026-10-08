-- Private address book is independent from immutable trade selections.
CREATE TABLE lifecycle_address_book (
 id INTEGER PRIMARY KEY,
 owner_id INTEGER NOT NULL REFERENCES users(id),
 version INTEGER NOT NULL DEFAULT 1 CHECK(version>0),
 label TEXT NOT NULL DEFAULT '',
 is_default INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0,1)),
 first_name TEXT NOT NULL, last_name TEXT NOT NULL, street TEXT NOT NULL,
 house_number TEXT NOT NULL, postal_code TEXT NOT NULL, city TEXT NOT NULL, country TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX lifecycle_address_default ON lifecycle_address_book(owner_id) WHERE is_default=1;
CREATE TABLE lifecycle_address_book_commands (
 owner_id INTEGER NOT NULL REFERENCES users(id), command_key TEXT NOT NULL,
 operation TEXT NOT NULL, payload_digest TEXT NOT NULL, result_json TEXT NOT NULL,
 created_at TEXT NOT NULL, PRIMARY KEY(owner_id,command_key)
);
CREATE TABLE lifecycle_address_snapshots (
 id INTEGER PRIMARY KEY, trade_id INTEGER NOT NULL REFERENCES lifecycle_contracts(trade_id),
 owner_id INTEGER NOT NULL REFERENCES users(id), revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id),
 basis_json TEXT NOT NULL CHECK(json_valid(basis_json)), schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version=1),
 first_name TEXT NOT NULL, last_name TEXT NOT NULL, street TEXT NOT NULL,
 house_number TEXT NOT NULL, postal_code TEXT NOT NULL, city TEXT NOT NULL, country TEXT NOT NULL,
 selected_at TEXT NOT NULL
);
CREATE TABLE lifecycle_address_choices (
 trade_id INTEGER NOT NULL REFERENCES lifecycle_contracts(trade_id),
 owner_id INTEGER NOT NULL REFERENCES users(id), generation INTEGER NOT NULL CHECK(generation>0),
 snapshot_id INTEGER NOT NULL REFERENCES lifecycle_address_snapshots(id),
 PRIMARY KEY(trade_id,owner_id)
);
CREATE TABLE lifecycle_address_releases (
 trade_id INTEGER PRIMARY KEY REFERENCES lifecycle_contracts(trade_id),
 revision_id INTEGER NOT NULL REFERENCES lifecycle_revisions(id), basis_json TEXT NOT NULL CHECK(json_valid(basis_json)),
 requester_snapshot_id INTEGER NOT NULL REFERENCES lifecycle_address_snapshots(id),
 partner_snapshot_id INTEGER NOT NULL REFERENCES lifecycle_address_snapshots(id),
 released_at TEXT NOT NULL
);
CREATE TRIGGER lifecycle_address_book_owner BEFORE UPDATE OF id,owner_id,created_at ON lifecycle_address_book
BEGIN SELECT RAISE(ABORT,'Address ownership is immutable'); END;
CREATE TRIGGER lifecycle_address_snapshot_owner BEFORE INSERT ON lifecycle_address_snapshots
WHEN NOT EXISTS(SELECT 1 FROM lifecycle_contracts c JOIN trades t ON t.id=c.trade_id
 WHERE c.trade_id=NEW.trade_id AND c.state='accepted' AND c.accepted_revision_id=NEW.revision_id
 AND NEW.owner_id IN(t.requester_user_id,t.partner_user_id))
 OR EXISTS(SELECT 1 FROM lifecycle_address_releases WHERE trade_id=NEW.trade_id)
BEGIN SELECT RAISE(ABORT,'Invalid private address selection'); END;
CREATE TRIGGER lifecycle_address_snapshot_immutable BEFORE UPDATE ON lifecycle_address_snapshots
BEGIN SELECT RAISE(ABORT,'Trade address snapshot is immutable'); END;
-- No delete prohibition: a separately authorized privacy erasure may remove
-- release/selection metadata then snapshots. No erasure schedule is invented.
CREATE TRIGGER lifecycle_address_choice_insert BEFORE INSERT ON lifecycle_address_choices
WHEN EXISTS(SELECT 1 FROM lifecycle_address_releases WHERE trade_id=NEW.trade_id)
 OR NOT EXISTS(SELECT 1 FROM lifecycle_address_snapshots WHERE id=NEW.snapshot_id AND trade_id=NEW.trade_id AND owner_id=NEW.owner_id)
BEGIN SELECT RAISE(ABORT,'Invalid address choice'); END;
CREATE TRIGGER lifecycle_address_choice_update BEFORE UPDATE ON lifecycle_address_choices
WHEN EXISTS(SELECT 1 FROM lifecycle_address_releases WHERE trade_id=OLD.trade_id)
 OR NEW.trade_id<>OLD.trade_id OR NEW.owner_id<>OLD.owner_id OR NEW.generation<>OLD.generation+1
 OR NOT EXISTS(SELECT 1 FROM lifecycle_address_snapshots WHERE id=NEW.snapshot_id AND trade_id=NEW.trade_id AND owner_id=NEW.owner_id)
BEGIN SELECT RAISE(ABORT,'Address choice is stale or released'); END;
CREATE TRIGGER lifecycle_address_release_owner BEFORE INSERT ON lifecycle_address_releases
WHEN NOT EXISTS(SELECT 1 FROM trades t JOIN lifecycle_contracts c ON c.trade_id=t.id
 JOIN lifecycle_address_snapshots a ON a.id=NEW.requester_snapshot_id
 JOIN lifecycle_address_snapshots b ON b.id=NEW.partner_snapshot_id
 JOIN lifecycle_address_choices ac ON ac.trade_id=t.id AND ac.owner_id=t.requester_user_id AND ac.snapshot_id=a.id
 JOIN lifecycle_address_choices bc ON bc.trade_id=t.id AND bc.owner_id=t.partner_user_id AND bc.snapshot_id=b.id
 WHERE t.id=NEW.trade_id AND c.accepted_revision_id=NEW.revision_id AND c.state='accepted'
 AND a.trade_id=t.id AND b.trade_id=t.id AND a.owner_id=t.requester_user_id AND b.owner_id=t.partner_user_id
 AND a.revision_id=NEW.revision_id AND b.revision_id=NEW.revision_id
 AND a.basis_json=NEW.basis_json AND b.basis_json=NEW.basis_json)
BEGIN SELECT RAISE(ABORT,'Release requires both current owned snapshots'); END;
CREATE TRIGGER lifecycle_address_release_immutable BEFORE UPDATE ON lifecycle_address_releases
BEGIN SELECT RAISE(ABORT,'Address release is immutable'); END;
CREATE TRIGGER lifecycle_address_snapshot_no_replace BEFORE INSERT ON lifecycle_address_snapshots
WHEN EXISTS(SELECT 1 FROM lifecycle_address_snapshots WHERE id=NEW.id)
BEGIN SELECT RAISE(ABORT,'Address snapshot identity exists'); END;
CREATE TRIGGER lifecycle_address_release_no_replace BEFORE INSERT ON lifecycle_address_releases
WHEN EXISTS(SELECT 1 FROM lifecycle_address_releases WHERE trade_id=NEW.trade_id)
BEGIN SELECT RAISE(ABORT,'Address release already exists'); END;
