"""Standalone, database-free Journey V2 design preview. Run directly; port 8093."""
from pathlib import Path
from flask import Flask, render_template
from trade_visual_preview import ALBUMS, GIVE, register_trade_visual_preview


def create_app():
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"),
                static_folder=str(Path(__file__).parent / "static"))
    app.config["SAMMLR_ENV"] = "development"
    register_trade_visual_preview(app)

    @app.get("/preview/sammlrpax-journey-v2")
    def journey_v2():
        return render_template("sammlrpax_journey_v2.html", incoming=ALBUMS, outgoing=GIVE)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8093, debug=False)
