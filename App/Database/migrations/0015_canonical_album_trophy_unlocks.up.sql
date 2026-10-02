CREATE TABLE canonical_trophy_unlocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL UNIQUE,
    trophy_definition_id TEXT NOT NULL,
    user_album_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    trophy_name TEXT NOT NULL,
    unlocked_at TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_key TEXT NOT NULL,
    trigger_sticker_code TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_album_id, user_id, album_id)
        REFERENCES user_albums(id, user_id, album_id) ON DELETE CASCADE,
    CHECK (length(trim(event_key)) > 0),
    CHECK (length(trim(trophy_definition_id)) > 0),
    CHECK (length(trim(trophy_name)) > 0),
    CHECK (length(trim(unlocked_at)) > 0),
    CHECK (source_type IN ('inventory_transition', 'album_completion')),
    CHECK (length(trim(source_key)) > 0),
    CHECK (
        trigger_sticker_code IS NULL
        OR length(trim(trigger_sticker_code)) > 0
    ),
    UNIQUE (user_album_id, trophy_definition_id)
);

CREATE INDEX idx_cb005_trophy_unlocks_user_time
    ON canonical_trophy_unlocks(user_id, unlocked_at DESC, id DESC);

CREATE INDEX idx_cb005_trophy_unlocks_album_time
    ON canonical_trophy_unlocks(user_album_id, unlocked_at, id);
