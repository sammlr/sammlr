"""Generate synthetic test DBs from SQL, only inside a temporary candidate."""

from pathlib import Path
import sqlite3

from App.Database.migration_runner import migrate


def prepare() -> None:
    root = Path(__file__).resolve().parents[1]
    if not root.is_relative_to(Path('/private/tmp')):
        raise RuntimeError('Test fixture generation requires an isolated /private/tmp candidate')
    sql = (root / 'App/Database/sammlr_reference_s00.sql').read_text()
    targets = [root / 'App/Database' / name for name in (
        'sammlr_reference_s00.db', 'sammlr.db')]
    if any(path.exists() or path.is_symlink() for path in targets):
        raise FileExistsError('Refusing to replace existing test databases')
    for path in targets:
        with path.open('xb'):
            pass
        with sqlite3.connect(path) as connection:
            connection.executescript(sql)
            if path.name == 'sammlr.db':
                migrate(connection, target_version=20)


if __name__ == '__main__':
    prepare()
