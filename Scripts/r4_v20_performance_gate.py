"""Build and measure the reproducible R4 schema-V20 performance gate."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(APP_DIR))

from App.Database.migration_runner import current_version, migrate  # noqa: E402
from services.auth_security import (  # noqa: E402
    WERKZEUG_PASSWORD_SCHEME,
    canonical_password_hash,
)


SCHEMA_VERSION = 20
PASSWORD = "r4-performance-only"
CSRF_RE = re.compile(r'name="_csrf_token" value="([^"]+)"')


@dataclass(frozen=True)
class DatasetScale:
    users: int = 100
    albums: int = 10
    stickers_per_album: int = 100
    trades: int = 2_000
    notifications: int = 5_000
    friendships: int = 1_000


DEFAULT_SCALE = DatasetScale()
CONCURRENCY = 20
TYPICAL_SAMPLES = 5


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_private_tmp(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(Path("/private/tmp")):
        raise ValueError(f"{label} must be under /private/tmp")
    return resolved


def prepare_database(target: Path, scale: DatasetScale = DEFAULT_SCALE) -> dict:
    target = _require_private_tmp(target, "performance database")
    if target.exists():
        raise FileExistsError(target)
    shutil.copy2(FIXTURE, target)
    password_hash = canonical_password_hash(PASSWORD)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with sqlite3.connect(target) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        migrate(connection, SCHEMA_VERSION)
        tables = connection.execute(
            """SELECT name FROM sqlite_master
               WHERE type='table' AND name NOT IN ('schema_migrations','sqlite_sequence')"""
        ).fetchall()
        for (table,) in tables:
            connection.execute(f'DELETE FROM "{table}"')

        connection.executemany(
            """INSERT INTO users
               (id, name, username, password, password_scheme, auth_version, account_state)
               VALUES (?, ?, ?, ?, ?, 1, 'active')""",
            ((user_id, f"Performance User {user_id}", f"perf_user_{user_id:03d}",
              password_hash, WERKZEUG_PASSWORD_SCHEME)
             for user_id in range(1, scale.users + 1)),
        )
        connection.executemany(
            """INSERT INTO albums (id, name, season, total, complete, cover)
               VALUES (?, ?, 'R4', ?, ?, 'P')""",
            ((f"perf{album:02d}", f"Performance Album {album}",
              scale.stickers_per_album, scale.stickers_per_album)
             for album in range(1, scale.albums + 1)),
        )
        connection.executemany(
            """INSERT INTO user_albums
               (user_id, album_id, visibility, trade_pool_enabled)
               VALUES (?, ?, 'public', 1)""",
            ((user, f"perf{album:02d}")
             for user in range(1, scale.users + 1)
             for album in range(1, scale.albums + 1)),
        )
        connection.executemany(
            """INSERT INTO stickers
               (album_id, sticker_code, status, duplicates, quantity, user_id)
               VALUES (?, ?, 'owned', ?, ?, ?)""",
            ((f"perf{album:02d}", f"PERF {code:03d}", quantity - 1, quantity, user)
             for user in range(1, scale.users + 1)
             for album in range(1, scale.albums + 1)
             for code in range(1, scale.stickers_per_album + 1)
             for quantity in (2 if (user + album + code) % 5 == 0 else 1,)),
        )
        statuses = ("open", "accepted", "completed", "completed")
        connection.executemany(
            """INSERT INTO trade_requests
               (album_id, from_user_id, to_user_id, give_codes, get_codes, status,
                from_confirmed, to_confirmed, created_at)
               VALUES (?, ?, ?, '["PERF 001"]', '["PERF 002"]', ?, 0, 0, ?)""",
            ((f"perf{(index % scale.albums) + 1:02d}",
              (index % scale.users) + 1,
              ((index + 1) % scale.users) + 1,
              statuses[index % len(statuses)],
              (now - timedelta(minutes=index % (14 * 24 * 60))).strftime(
                  "%Y-%m-%d %H:%M:%S"
              )) for index in range(scale.trades)),
        )
        connection.executemany(
            """INSERT INTO notifications
               (user_id, title, body, is_read, notification_type, created_at)
               VALUES (?, 'R4 Baseline', 'Temporäre Lasttestnachricht', ?, 'legacy', ?)""",
            (((index % scale.users) + 1, index % 2,
              (now - timedelta(minutes=index % (20 * 24 * 60))).strftime(
                  "%Y-%m-%d %H:%M:%S"
              )) for index in range(scale.notifications)),
        )
        pairs = ((low, high) for low in range(1, scale.users + 1)
                 for high in range(low + 1, scale.users + 1))
        connection.executemany(
            "INSERT INTO friendships (user_low_id, user_high_id) VALUES (?, ?)",
            (pair for _, pair in zip(range(scale.friendships), pairs)),
        )
        connection.commit()
        connection.execute("PRAGMA foreign_keys=ON")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        counts = {table: connection.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0] for table in (
            "users", "albums", "stickers", "trade_requests", "notifications",
            "friendships",
        )}
        schema = current_version(connection)
        pragmas = {
            "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
            "busy_timeout_ms": connection.execute("PRAGMA busy_timeout").fetchone()[0],
        }
    return {
        "database": str(target), "database_sha256": sha256(target),
        "schema_version": schema, "scale": asdict(scale), "counts": counts,
        "integrity": integrity, "foreign_key_violations": len(foreign_keys),
        "pragmas": pragmas,
    }


QUERY_PLAN_CASES = {
    "trade_user_status_time": (
        """SELECT * FROM trade_requests
           WHERE (from_user_id=? OR to_user_id=?) AND status IN ('open','accepted')
           ORDER BY created_at DESC""", (1, 1)),
    "trade_user_lookup": (
        """SELECT album_id, from_user_id, to_user_id FROM trade_requests
           WHERE status IN ('open','accepted')
             AND (from_user_id=? OR to_user_id=?)""", (1, 1)),
    "notification_unread": (
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (1,)),
    "notification_page_time": (
        """SELECT * FROM notifications WHERE user_id=?
           ORDER BY created_at DESC, id DESC LIMIT 25 OFFSET 0""", (1,)),
    "notification_retention": (
        """DELETE FROM notifications
           WHERE user_id=? AND is_read=1 AND created_at < ?""",
        (1, "2000-01-01 00:00:00")),
}


def inspect_query_plans(database: Path) -> dict:
    with sqlite3.connect(database) as connection:
        return {
            name: [row[3] for row in connection.execute(
                "EXPLAIN QUERY PLAN " + statement, parameters
            ).fetchall()]
            for name, (statement, parameters) in QUERY_PLAN_CASES.items()
        }


def verify_database(database: Path) -> dict:
    with sqlite3.connect(database) as connection:
        return {
            "database_sha256": sha256(database),
            "schema_version": current_version(connection),
            "integrity": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_violations": len(
                connection.execute("PRAGMA foreign_key_check").fetchall()
            ),
            "counts": {
                table: connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
                for table in (
                    "users", "albums", "stickers", "trade_requests",
                    "notifications", "friendships",
                )
            },
        }


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _cookie_value(headers):
    parsed = SimpleCookie()
    for value in headers.get_all("Set-Cookie") or ():
        parsed.load(value)
    return "; ".join(f"{key}={morsel.value}" for key, morsel in parsed.items())


class _SessionOpener:
    def __init__(self, cookie, csrf):
        self.cookie = cookie
        self.csrf = csrf
        self.opener = build_opener()

    def open(self, url, method="GET", timeout=10):
        data = None
        headers = {"Cookie": self.cookie}
        if method == "POST":
            data = urlencode({"_csrf_token": self.csrf}).encode()
            headers["X-CSRF-Token"] = self.csrf
        return self.opener.open(Request(url, data=data, headers=headers), timeout=timeout)


def _csrf_login(base_url: str, username: str):
    no_redirect = build_opener(_NoRedirect())
    initial = no_redirect.open(base_url + "/login", timeout=10)
    page = initial.read().decode("utf-8")
    cookie = _cookie_value(initial.headers)
    token = CSRF_RE.search(page).group(1)
    payload = urlencode({
        "username": username, "password": PASSWORD, "_csrf_token": token,
    }).encode()
    login_request = Request(
        base_url + "/login", data=payload,
        headers={"Cookie": cookie, "X-CSRF-Token": token},
    )
    try:
        no_redirect.open(login_request, timeout=15)
        raise RuntimeError("performance login did not redirect")
    except HTTPError as response:
        if response.code != 302 or response.headers.get("Location") != "/":
            raise
        cookie = _cookie_value(response.headers) or cookie
    authenticated = _SessionOpener(cookie, "")
    authenticated_page = authenticated.open(base_url + "/").read().decode("utf-8")
    authenticated.csrf = CSRF_RE.search(authenticated_page).group(1)
    return authenticated


def _single_request(opener, url, method="GET"):
    started = time.perf_counter()
    try:
        if isinstance(opener, _SessionOpener):
            response = opener.open(url, method=method, timeout=10)
        else:
            response = opener.open(url, timeout=10)
        status = response.status
        response.read()
    except HTTPError as error:
        return (time.perf_counter() - started) * 1000, error.code, f"HTTP {error.code}"
    except Exception as error:
        return (time.perf_counter() - started) * 1000, 0, type(error).__name__
    return (time.perf_counter() - started) * 1000, status, None


def _percentile(values, percentile):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]


def _summarize(samples):
    durations = [sample[0] for sample in samples]
    errors = [sample[2] or f"HTTP {sample[1]}" for sample in samples
              if sample[1] != 200]
    return {
        "requests": len(samples), "median_ms": round(statistics.median(durations), 3),
        "p95_ms": round(_percentile(durations, 0.95), 3),
        "max_ms": round(max(durations), 3), "error_count": len(errors),
        "errors": sorted(set(errors)),
    }


def _classify(typical, stress):
    if typical["error_count"] or stress["error_count"] or stress["p95_ms"] > 1000:
        return "RED"
    return "GREEN" if stress["p95_ms"] < 500 else "YELLOW"


def sqlite_lock_probe(database: Path) -> dict:
    writer = sqlite3.connect(database, timeout=0.25)
    contender = sqlite3.connect(database, timeout=0.25)
    reader = sqlite3.connect(database, timeout=0.25)
    try:
        configured_busy_timeout = writer.execute("PRAGMA busy_timeout").fetchone()[0]
        journal_mode = writer.execute("PRAGMA journal_mode").fetchone()[0]
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE users SET name=name WHERE id=1")
        read_started = time.perf_counter()
        reader.execute("SELECT COUNT(*) FROM users").fetchone()
        read_ms = (time.perf_counter() - read_started) * 1000
        write_started = time.perf_counter()
        locked = False
        error = None
        try:
            contender.execute("UPDATE users SET name=name WHERE id=2")
        except sqlite3.OperationalError as exception:
            locked = "locked" in str(exception).lower()
            error = str(exception)
        wait_ms = (time.perf_counter() - write_started) * 1000
        writer.rollback()
        contender.rollback()
        return {
            "journal_mode": journal_mode,
            "connection_busy_timeout_ms": configured_busy_timeout,
            "reader_during_write_ms": round(read_ms, 3),
            "competing_write_wait_ms": round(wait_ms, 3),
            "competing_write_locked": locked,
            "competing_write_error": error,
            "data_preserved": writer.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0] > 0,
        }
    finally:
        writer.close()
        contender.close()
        reader.close()


FLOWS = {
    "login": ("/login", "GET", False),
    "home": ("/", "GET", True),
    "collection": ("/sammlung", "GET", True),
    "album": ("/album/perf01", "GET", True),
    "stickerwall_missing": ("/album/perf01?filter=missing", "GET", True),
    "partner_search": ("/profil/freunde?q=perf_user", "GET", True),
    "trade_market": ("/trades", "GET", True),
    "trade_requests": ("/trades?tab=requests", "GET", True),
    "album_trade_hub": ("/album/perf01/trades?tab=requests", "GET", True),
    "deal": ("/trades/1", "GET", True),
    "notifications_gate": ("/notifications", "GET", True),
    "notifications_inbox": ("/notifications", "POST", True),
    "profile": ("/profil", "GET", True),
    "public_profile": ("/profil/perf_user_002", "GET", True),
    "public_stickerwall": ("/profil/perf_user_002/album/perf01", "GET", True),
}


def run_http_gate(database: Path, python: Path, port: int) -> dict:
    environment = os.environ.copy()
    environment.update({
        "SAMMLR_ENV": "production",
        "SAMMLR_SECRET_KEY": "r4-isolated-performance-secret",
        "SAMMLR_R4_PERFORMANCE_GATE": "1",
        "DATABASE_PATH": str(database.resolve()), "PORT": str(port),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    next_port = port

    def start_server():
        nonlocal next_port
        server_port = next_port
        next_port += 1
        base_url = f"http://127.0.0.1:{server_port}"
        environment["PORT"] = str(server_port)
        server = subprocess.Popen(
            [str(python), "-m", "gunicorn", "--workers", "1", "--threads", "20",
             "--bind", f"127.0.0.1:{server_port}", "--access-logfile", "/dev/null",
             "--error-logfile", "-", "performance_wsgi:app"],
            cwd=APP_DIR, env=environment, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, text=True, start_new_session=True,
        )
        healthy = False
        for _ in range(60):
            try:
                healthy = urlopen(base_url + "/healthz", timeout=30).status == 200
                break
            except Exception:
                time.sleep(0.25)
        if not healthy:
            os.killpg(server.pid, signal.SIGTERM)
            _, boot_error = server.communicate(timeout=10)
            raise RuntimeError(
                "Gunicorn V20 performance gate did not become healthy: "
                + boot_error.strip()
            )
        return server, base_url

    def stop_server(server):
        try:
            os.killpg(server.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(server.pid, signal.SIGKILL)
            server.wait(timeout=5)

    server, base_url = start_server()
    try:
        anonymous = build_opener()
        openers = [_csrf_login(base_url, f"perf_user_{index:03d}")
                   for index in range(1, CONCURRENCY + 1)]
        stop_server(server)
        server = None
        results = {}
        flow_items = list(FLOWS.items())
        for name, (path, method, authenticated) in flow_items:
            server, base_url = start_server()
            pool = openers if authenticated else [anonymous] * CONCURRENCY
            _single_request(pool[0], base_url + path, method)
            typical = [_single_request(pool[0], base_url + path, method)
                       for _ in range(TYPICAL_SAMPLES)]
            with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
                stress = list(executor.map(
                    lambda opener: _single_request(opener, base_url + path, method), pool
                ))
            typical_summary = _summarize(typical)
            stress_summary = _summarize(stress)
            results[name] = {
                "path": path, "method": method, "typical": typical_summary,
                "concurrent_20": stress_summary,
                "classification": _classify(typical_summary, stress_summary),
            }
            stop_server(server)
            server = None
        return {
            "server": "gunicorn", "workers": 1, "threads": 20,
            "concurrency": CONCURRENCY, "typical_samples": TYPICAL_SAMPLES,
            "flows": results,
        }
    finally:
        if server is not None:
            stop_server(server)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--port", type=int, default=18085)
    args = parser.parse_args()
    output = _require_private_tmp(args.output, "performance output")
    python = args.python if args.python.is_absolute() else PROJECT_ROOT / args.python
    prepared = prepare_database(args.database)
    report = {
        "gate": "R4 V20 PERFORMANCE GATE", "dataset": prepared,
        "query_plans": inspect_query_plans(args.database),
        "sqlite_lock_probe": sqlite_lock_probe(args.database),
        **run_http_gate(args.database, python, args.port),
    }
    report["post_measurement_database"] = verify_database(args.database)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
