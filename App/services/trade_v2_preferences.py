"""One persisted preference per existing user-album membership; no auto migration."""
from services.trade_v2_rules import mode


class TradeV2Preferences:
    def __init__(self, connection):
        self.db = connection
        self.available = 'cross_album_mode' in {
            r[1] for r in connection.execute('PRAGMA table_info(user_albums)')
        }

    def read(self, user_ids):
        ids = tuple(sorted(set(user_ids)))
        if not ids:
            return {}
        expression = 'cross_album_mode' if self.available else 'NULL'
        rows = self.db.execute(
            f'SELECT user_id,album_id,{expression} FROM user_albums '
            f'WHERE user_id IN ({",".join("?" for _ in ids)})', ids)
        return {(r[0], r[1]): mode(r[2]) for r in rows}

    def set_mode(self, user_id, album_id, value):
        """Internal explicit write hook. Caller owns auth/transaction; no HTTP route."""
        value = mode(value)
        if not self.available:
            raise ValueError('Migration 0022 is required to persist preferences')
        if type(user_id) is not int or user_id <= 0:
            raise ValueError('Invalid preference owner')
        result = self.db.execute('UPDATE user_albums SET cross_album_mode=? WHERE user_id=? AND album_id=?',
                                 (value, user_id, album_id))
        if result.rowcount != 1:
            raise ValueError('Album membership does not exist')
