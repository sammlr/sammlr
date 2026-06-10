import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from App.Database import database

app = Flask(__name__)
app.secret_key = 'your_secret_key'

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