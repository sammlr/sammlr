-- Legacy V0 schema, separated from the synthetic S00 fixture. No user data.
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
