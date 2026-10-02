CREATE UNIQUE INDEX idx_s33_stickers_identity
    ON stickers(user_id, album_id, sticker_code);

CREATE TRIGGER s33_stickers_validate_insert
BEFORE INSERT ON stickers
BEGIN
    SELECT CASE
        WHEN NEW.user_id IS NULL
          OR NEW.album_id IS NULL
          OR NEW.sticker_code IS NULL
          OR NEW.quantity IS NULL
          OR NEW.quantity < 1
          OR NEW.duplicates IS NULL
          OR NEW.duplicates <> NEW.quantity - 1
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.user_id)
          OR NOT EXISTS (SELECT 1 FROM albums WHERE id=NEW.album_id)
        THEN RAISE(ABORT, 'invalid sticker inventory row')
    END;
END;

CREATE TRIGGER s33_stickers_validate_update
BEFORE UPDATE ON stickers
BEGIN
    SELECT CASE
        WHEN NEW.user_id IS NULL
          OR NEW.album_id IS NULL
          OR NEW.sticker_code IS NULL
          OR NEW.quantity IS NULL
          OR NEW.quantity < 1
          OR NEW.duplicates IS NULL
          OR NEW.duplicates <> NEW.quantity - 1
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.user_id)
          OR NOT EXISTS (SELECT 1 FROM albums WHERE id=NEW.album_id)
        THEN RAISE(ABORT, 'invalid sticker inventory row')
    END;
END;

CREATE TRIGGER s33_user_albums_validate_insert
BEFORE INSERT ON user_albums
BEGIN
    SELECT CASE
        WHEN NEW.user_id IS NULL
          OR NEW.album_id IS NULL
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.user_id)
          OR NOT EXISTS (SELECT 1 FROM albums WHERE id=NEW.album_id)
        THEN RAISE(ABORT, 'invalid user album reference')
    END;
END;

CREATE TRIGGER s33_user_albums_validate_update
BEFORE UPDATE ON user_albums
BEGIN
    SELECT CASE
        WHEN NEW.user_id IS NULL
          OR NEW.album_id IS NULL
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.user_id)
          OR NOT EXISTS (SELECT 1 FROM albums WHERE id=NEW.album_id)
        THEN RAISE(ABORT, 'invalid user album reference')
    END;
END;

CREATE TRIGGER s33_notifications_validate_insert
BEFORE INSERT ON notifications
BEGIN
    SELECT CASE
        WHEN NEW.user_id IS NULL
          OR NEW.is_read IS NULL
          OR NEW.is_read NOT IN (0, 1)
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.user_id)
        THEN RAISE(ABORT, 'invalid notification row')
    END;
END;

CREATE TRIGGER s33_notifications_validate_update
BEFORE UPDATE ON notifications
BEGIN
    SELECT CASE
        WHEN NEW.user_id IS NULL
          OR NEW.is_read IS NULL
          OR NEW.is_read NOT IN (0, 1)
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.user_id)
        THEN RAISE(ABORT, 'invalid notification row')
    END;
END;

CREATE TRIGGER s33_trade_requests_validate_insert
BEFORE INSERT ON trade_requests
BEGIN
    SELECT CASE
        WHEN NEW.album_id IS NULL
          OR NEW.from_user_id IS NULL
          OR NEW.to_user_id IS NULL
          OR NEW.from_user_id = NEW.to_user_id
          OR NEW.status IS NULL
          OR NEW.status NOT IN (
              'open', 'accepted', 'declined', 'completed', 'failed',
              'cancelled', 'expired', 'obsolete'
          )
          OR NEW.from_confirmed IS NULL
          OR NEW.from_confirmed NOT IN (-22, 0, 1)
          OR NEW.to_confirmed IS NULL
          OR NEW.to_confirmed NOT IN (0, 1)
          OR NOT EXISTS (SELECT 1 FROM albums WHERE id=NEW.album_id)
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.from_user_id)
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.to_user_id)
        THEN RAISE(ABORT, 'invalid trade request row')
    END;
END;

CREATE TRIGGER s33_trade_requests_validate_update
BEFORE UPDATE ON trade_requests
BEGIN
    SELECT CASE
        WHEN NEW.album_id IS NULL
          OR NEW.from_user_id IS NULL
          OR NEW.to_user_id IS NULL
          OR NEW.from_user_id = NEW.to_user_id
          OR NEW.status IS NULL
          OR NEW.status NOT IN (
              'open', 'accepted', 'declined', 'completed', 'failed',
              'cancelled', 'expired', 'obsolete'
          )
          OR NEW.from_confirmed IS NULL
          OR NEW.from_confirmed NOT IN (-22, 0, 1)
          OR NEW.to_confirmed IS NULL
          OR NEW.to_confirmed NOT IN (0, 1)
          OR NOT EXISTS (SELECT 1 FROM albums WHERE id=NEW.album_id)
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.from_user_id)
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.to_user_id)
        THEN RAISE(ABORT, 'invalid trade request row')
    END;
END;

CREATE TRIGGER s33_unlocked_trophies_validate_insert
BEFORE INSERT ON unlocked_trophies
BEGIN
    SELECT CASE
        WHEN NEW.user_id IS NULL
          OR NEW.album_id IS NULL
          OR NEW.trophy_name IS NULL
          OR NEW.trophy_name = ''
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.user_id)
          OR (
              NEW.album_id <> '__global__'
              AND NOT EXISTS (SELECT 1 FROM albums WHERE id=NEW.album_id)
          )
        THEN RAISE(ABORT, 'invalid trophy unlock row')
    END;
END;

CREATE TRIGGER s33_unlocked_trophies_validate_update
BEFORE UPDATE ON unlocked_trophies
BEGIN
    SELECT CASE
        WHEN NEW.user_id IS NULL
          OR NEW.album_id IS NULL
          OR NEW.trophy_name IS NULL
          OR NEW.trophy_name = ''
          OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.user_id)
          OR (
              NEW.album_id <> '__global__'
              AND NOT EXISTS (SELECT 1 FROM albums WHERE id=NEW.album_id)
          )
        THEN RAISE(ABORT, 'invalid trophy unlock row')
    END;
END;
