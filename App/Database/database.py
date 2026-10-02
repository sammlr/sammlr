import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from App.Database import database

app = Flask(__name__)
# Use the same environment contract as App/webapp.py; never a known fallback.
app.config["SECRET_KEY"] = os.environ.get("SAMMLR_SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("SAMMLR_SECRET_KEY is required")

def init_db():
    con = database.get_db()
    cur = con.cursor()
    try:
        cur.execute("ALTER TABLE trade_requests ADD COLUMN from_confirmed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    con.commit()
    con.close()

# rest of your webapp.py code follows...