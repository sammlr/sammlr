"""Explicitly isolated R4 schema-V20 Gunicorn performance harness."""

from pathlib import Path
import os

from services import runtime_operations


if os.environ.get("SAMMLR_R4_PERFORMANCE_GATE") != "1":
    raise RuntimeError("R4 performance harness requires explicit opt-in")

database_path = Path(os.environ.get("DATABASE_PATH", "")).resolve()
if not database_path.is_relative_to(Path("/private/tmp")):
    raise RuntimeError("R4 performance database must be isolated under /private/tmp")

runtime_operations.PRODUCTION_DATABASE_PATH = database_path

import webapp  # noqa: E402
from services import album_completion, statistics_projection, trophy_unlocks  # noqa: E402


_product_all_codes = webapp.all_codes


def _performance_catalog_codes(album_id):
    """Expose the synthetic 100-slot R4 catalogs to the real route code."""

    if str(album_id).startswith("perf"):
        return [f"PERF {code:03d}" for code in range(1, 101)]
    return _product_all_codes(album_id)


webapp.all_codes = _performance_catalog_codes
album_completion.all_codes = _performance_catalog_codes
statistics_projection.all_codes = _performance_catalog_codes
trophy_unlocks.all_codes = _performance_catalog_codes
app = webapp.app
# Loopback Safari/WebDriver uses HTTP. This exception exists only behind the
# mandatory R4 harness opt-in above; the production app keeps Secure cookies.
app.config["SESSION_COOKIE_SECURE"] = False
