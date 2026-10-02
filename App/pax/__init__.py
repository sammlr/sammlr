"""PAX-01–03: isolated, database-free demonstration application."""
from pathlib import Path
from flask import Flask


def create_app():
    root = Path(__file__).resolve().parents[1]
    app = Flask(__name__, template_folder=str(root / 'templates'),
                static_folder=str(root / 'static'))
    from .routes import preview
    app.register_blueprint(preview)
    return app
