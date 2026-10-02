CREATE TABLE user_profile_stickers_v0019 (
    user_id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    country_code TEXT NOT NULL DEFAULT 'DE',
    club_name TEXT NOT NULL DEFAULT '',
    accent_color TEXT NOT NULL DEFAULT 'purple',
    portrait_filename TEXT,
    portrait_mime TEXT,
    portrait_width INTEGER,
    portrait_height INTEGER,
    crop_x REAL NOT NULL DEFAULT 0,
    crop_y REAL NOT NULL DEFAULT 0,
    crop_zoom REAL NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CHECK (length(trim(display_name)) BETWEEN 1 AND 32),
    CHECK (country_code IN ('DE', 'NL', 'FR', 'IT', 'BE', 'IE', 'RO')),
    CHECK (length(club_name) <= 48),
    CHECK (accent_color IN ('purple', 'red', 'blue', 'yellow', 'green', 'orange', 'black', 'cream')),
    CHECK (portrait_filename IS NULL OR portrait_filename GLOB '[0-9a-f]*.*'),
    CHECK (portrait_mime IS NULL OR portrait_mime IN ('image/jpeg', 'image/png')),
    CHECK (crop_x BETWEEN -35 AND 35),
    CHECK (crop_y BETWEEN -35 AND 35),
    CHECK (crop_zoom BETWEEN 1 AND 2.5)
);

INSERT INTO user_profile_stickers_v0019 (
    user_id, display_name, country_code, club_name, accent_color,
    portrait_filename, portrait_mime, portrait_width, portrait_height,
    crop_x, crop_y, crop_zoom, updated_at
)
SELECT
    user_id, display_name, country_code, club_name, accent_color,
    portrait_filename, portrait_mime, portrait_width, portrait_height,
    crop_x, crop_y, crop_zoom, updated_at
FROM user_profile_stickers;

DROP TABLE user_profile_stickers;
ALTER TABLE user_profile_stickers_v0019 RENAME TO user_profile_stickers;
