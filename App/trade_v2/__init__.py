"""Isolated, read-only Trade UX preview. No production application or DB import."""
from pathlib import Path
from flask import Flask


def create_app():
    root = Path(__file__).resolve().parent
    app = Flask(__name__, template_folder=str(root / 'templates'),
                static_folder=str(root.parent / 'static'))
    from .routes import preview
    app.register_blueprint(preview)
    return app
