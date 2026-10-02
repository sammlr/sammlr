CREATE UNIQUE INDEX idx_cb001_user_albums_context
    ON user_albums(id, user_id, album_id);

CREATE TABLE historical_album_records (
    user_album_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    started_at TEXT,
    start_event_key TEXT UNIQUE,
    completed_at TEXT,
    completion_event_key TEXT UNIQUE,
    completion_source_type TEXT,
    completion_source_key TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_album_id, user_id, album_id)
        REFERENCES user_albums(id, user_id, album_id) ON DELETE RESTRICT,
    CHECK (
        (started_at IS NULL AND start_event_key IS NULL)
        OR
        (started_at IS NOT NULL AND length(trim(started_at)) > 0
         AND start_event_key IS NOT NULL
         AND length(trim(start_event_key)) > 0)
    ),
    CHECK (
        (completed_at IS NULL
         AND completion_event_key IS NULL
         AND completion_source_type IS NULL
         AND completion_source_key IS NULL)
        OR
        (completed_at IS NOT NULL
         AND length(trim(completed_at)) > 0
         AND completion_event_key IS NOT NULL
         AND length(trim(completion_event_key)) > 0
         AND completion_source_type IN (
             'inventory_transition', 'validated_trophy'
         )
         AND completion_source_key IS NOT NULL
         AND length(trim(completion_source_key)) > 0)
    ),
    CHECK (started_at IS NOT NULL OR completed_at IS NOT NULL)
);

CREATE INDEX idx_cb001_album_records_user_time
    ON historical_album_records(user_id, completed_at, started_at, user_album_id);

CREATE TABLE historical_sticker_acquisitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_album_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    sticker_code TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    source_key TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_album_id, user_id, album_id)
        REFERENCES user_albums(id, user_id, album_id) ON DELETE RESTRICT,
    CHECK (length(trim(sticker_code)) > 0),
    CHECK (quantity > 0),
    CHECK (source_type IN ('inventory', 'paper_trade', 'trade_receipt')),
    CHECK (length(trim(source_key)) > 0),
    CHECK (length(trim(occurred_at)) > 0),
    UNIQUE (source_type, source_key, user_album_id, sticker_code)
);

CREATE INDEX idx_cb001_acquisitions_user_time
    ON historical_sticker_acquisitions(user_id, occurred_at, id);

CREATE INDEX idx_cb001_acquisitions_album_time
    ON historical_sticker_acquisitions(user_album_id, occurred_at, id);

CREATE TABLE historical_album_progress_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_album_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    event_key TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    owned_count INTEGER NOT NULL,
    total_count INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_album_id, user_id, album_id)
        REFERENCES user_albums(id, user_id, album_id) ON DELETE RESTRICT,
    CHECK (length(trim(event_key)) > 0),
    CHECK (length(trim(captured_at)) > 0),
    CHECK (owned_count >= 0),
    CHECK (total_count > 0),
    CHECK (owned_count <= total_count),
    UNIQUE (user_album_id, event_key)
);

CREATE INDEX idx_cb001_progress_album_time
    ON historical_album_progress_points(user_album_id, captured_at, id);

CREATE TABLE feed_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    actor_user_id INTEGER,
    user_album_id INTEGER,
    user_id INTEGER,
    album_id TEXT,
    target_type TEXT NOT NULL,
    target_key TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_album_id, user_id, album_id)
        REFERENCES user_albums(id, user_id, album_id) ON DELETE RESTRICT,
    CHECK (length(trim(event_key)) > 0),
    CHECK (event_type IN (
        'album_started',
        'album_progress',
        'album_completed',
        'trophy_unlocked',
        'trade_milestone',
        'sammlr_news'
    )),
    CHECK (target_type IN ('album', 'trophy', 'profile', 'trade', 'news')),
    CHECK (length(trim(target_key)) > 0),
    CHECK (length(trim(occurred_at)) > 0),
    CHECK (
        (event_type = 'sammlr_news' AND actor_user_id IS NULL)
        OR
        (event_type <> 'sammlr_news' AND actor_user_id IS NOT NULL)
    ),
    CHECK (
        (user_album_id IS NULL AND user_id IS NULL AND album_id IS NULL)
        OR
        (user_album_id IS NOT NULL AND user_id IS NOT NULL AND album_id IS NOT NULL)
    )
);

CREATE INDEX idx_cb001_feed_events_time
    ON feed_events(occurred_at DESC, id DESC);

CREATE INDEX idx_cb001_feed_events_actor_time
    ON feed_events(actor_user_id, occurred_at DESC, id DESC);

CREATE TABLE trophy_unlock_history_context (
    unlocked_trophy_id INTEGER PRIMARY KEY,
    user_album_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    trigger_sticker_code TEXT,
    trigger_source_key TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (unlocked_trophy_id)
        REFERENCES unlocked_trophies(id) ON DELETE CASCADE,
    FOREIGN KEY (user_album_id, user_id, album_id)
        REFERENCES user_albums(id, user_id, album_id) ON DELETE RESTRICT,
    CHECK (
        trigger_sticker_code IS NULL
        OR length(trim(trigger_sticker_code)) > 0
    ),
    CHECK (
        trigger_source_key IS NULL
        OR length(trim(trigger_source_key)) > 0
    )
);

CREATE INDEX idx_cb001_trophy_context_album
    ON trophy_unlock_history_context(user_album_id, unlocked_trophy_id);
