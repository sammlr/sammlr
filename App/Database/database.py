from flask import session
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "collectr.db"

def current_user_id():
    return session.get("user_id", 1)

def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con