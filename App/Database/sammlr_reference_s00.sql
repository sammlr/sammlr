-- Sammlr S00 reference fixture
-- Canonical source for App/Database/sammlr_reference_s00.db.
--
-- Safety: execute only against a new, empty SQLite file. The CREATE statements
-- intentionally omit IF NOT EXISTS so an existing Sammlr database is not
-- silently reused or overwritten.
--
-- All people, credentials, timestamps and collection states are synthetic.

PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TABLE albums (
    id TEXT PRIMARY KEY,
    name TEXT,
    season TEXT,
    total INTEGER,
    complete INTEGER,
    cover TEXT
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    body TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id TEXT,
    sticker_code TEXT,
    status TEXT,
    duplicates INTEGER DEFAULT 0,
    quantity INTEGER DEFAULT 1,
    user_id INTEGER DEFAULT 1
);

CREATE TABLE trade_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id TEXT,
    from_user_id INTEGER,
    to_user_id INTEGER,
    give_codes TEXT,
    get_codes TEXT,
    status TEXT DEFAULT 'open',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    from_confirmed INTEGER DEFAULT 0,
    to_confirmed INTEGER DEFAULT 0
);

CREATE TABLE unlocked_trophies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    album_id TEXT,
    trophy_name TEXT,
    unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, album_id, trophy_name)
);

CREATE TABLE user_albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    album_id TEXT,
    UNIQUE(user_id, album_id)
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    name TEXT,
    favorite_album_id TEXT
);

INSERT INTO albums (id, name, season, total, complete, cover) VALUES
    ('em24', 'EURO 2024', 'Germany', 728, 1, 'EURO'),
    ('vfl', 'VfL Osnabrück', '2024/25', 250, 0, 'VFL'),
    ('wm26', 'FIFA World Cup 2026', '2026', 992, 992, '🌍');

INSERT INTO users (id, username, password, name, favorite_album_id) VALUES
    (1, 'fixture_user_1', 'fixture-only', 'Fixture Person 1', 'vfl'),
    (2, 'fixture_user_2', 'fixture-only', 'Fixture Person 2', 'vfl'),
    (3, 'fixture_user_3', 'fixture-only', 'Fixture Person 3', 'em24');

INSERT INTO user_albums (id, user_id, album_id) VALUES
    (1, 1, 'vfl'),
    (2, 1, 'wm26'),
    (3, 2, 'vfl'),
    (4, 3, 'em24');

-- Quantities describe the deterministic state after trade_request 1 completed:
-- user 1 gave code 2 and received code 4; user 2 did the inverse.
INSERT INTO stickers
    (id, album_id, sticker_code, status, duplicates, quantity, user_id)
VALUES
    (1,  'vfl',  '1',      'owned', 2, 3, 1),
    (2,  'vfl',  '2',      'owned', 0, 1, 1),
    (3,  'vfl',  '4',      'owned', 0, 1, 1),
    (4,  'wm26', 'GER1',   'owned', 1, 2, 1),
    (5,  'wm26', '00',     'owned', 0, 1, 1),
    (6,  'vfl',  '2',      'owned', 0, 1, 2),
    (7,  'vfl',  '3',      'owned', 1, 2, 2),
    (8,  'vfl',  '4',      'owned', 0, 1, 2),
    (9,  'em24', 'EURO 8', 'owned', 0, 1, 3),
    (10, 'em24', '1',      'owned', 3, 4, 3);

INSERT INTO trade_requests
    (id, album_id, from_user_id, to_user_id, give_codes, get_codes, status,
     created_at, from_confirmed, to_confirmed)
VALUES
    (1, 'vfl', 1, 2, '["2"]', '["4"]', 'completed',
     '2026-01-15 12:00:00', 1, 1);

INSERT INTO notifications
    (id, user_id, title, body, is_read, created_at)
VALUES
    (1, 1, 'Fixture: Tausch abgeschlossen',
     'Der synthetische Referenztausch wurde verbucht.', 1,
     '2026-01-15 12:00:01'),
    (2, 2, 'Fixture: Tausch abgeschlossen',
     'Der synthetische Referenztausch wurde verbucht.', 0,
     '2026-01-15 12:00:01');

INSERT INTO unlocked_trophies
    (id, user_id, album_id, trophy_name, unlocked_at)
VALUES
    (1, 1, 'vfl', 'fixture_first_sticker', '2026-01-10 08:00:00');

COMMIT;

PRAGMA user_version = 1;
