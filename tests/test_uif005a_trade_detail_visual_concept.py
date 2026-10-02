from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASSETS = (
    ROOT
    / "Dokumentation"
    / "Post-RC"
    / "04-implementation-reports"
    / "assets"
    / "UIF-005A"
)


class UIF005ATradeDetailVisualConceptTests(unittest.TestCase):
    def _read(self, name):
        return (ASSETS / name).read_text(encoding="utf-8")

    def test_running_state_has_one_primary_action_and_required_information(self):
        html = self._read("trade-running.html")
        self.assertIn("Trade mit peter", html)
        self.assertIn("EURO 2024", html)
        self.assertIn("Warte auf deine Empfangsbestätigung", html)
        self.assertIn("Du bekommst", html)
        self.assertIn("UEFA 1", html)
        self.assertIn("Du gibst", html)
        self.assertIn("LEG 2", html)
        self.assertEqual(html.count('class="uif005a-primary"'), 1)
        self.assertIn("Alles vollständig erhalten", html)
        self.assertIn("Problem mit Lieferung melden", html)

    def test_running_state_is_explicit_visual_fixture_and_writes_nothing(self):
        html = self._read("trade-running.html")
        self.assertIn("Visual Fixture", html)
        self.assertNotIn("method=", html.lower())
        self.assertNotIn("action=", html.lower())

    def test_timeline_has_collapsed_and_expanded_visual_states(self):
        collapsed = self._read("trade-running.html")
        expanded = self._read("trade-running-timeline.html")
        self.assertIn("<details class=\"uif005a-timeline\">", collapsed)
        self.assertIn("<details class=\"uif005a-timeline\" open>", expanded)
        self.assertIn("Gesamten Verlauf anzeigen", collapsed)
        self.assertIn("Verlauf ausblenden", expanded)
        self.assertNotIn("<ol>", collapsed)
        self.assertNotIn("<ol>", expanded)
        self.assertEqual(expanded.count('role="listitem"'), 3)

    def test_collapsed_timeline_only_summarizes_latest_relevant_status(self):
        running = self._read("trade-running.html")
        completed = self._read("trade-completed.html")
        self.assertIn("uif005a-latest", running)
        self.assertIn("peter hat den Versand bestätigt", running)
        self.assertIn("Sticker sind unterwegs.", running)
        self.assertIn("uif005a-latest", completed)
        self.assertIn("Trade abgeschlossen", completed)
        self.assertIn("25.08.2026 · 21:28", completed)

    def test_completed_open_timeline_has_each_event_once(self):
        html = self._read("trade-completed-timeline.html")
        self.assertIn("<details class=\"uif005a-timeline\" open>", html)
        self.assertEqual(html.count('role="listitem"'), 6)
        timeline = html.split('<div class="uif005a-timeline-items"', 1)[1]
        for event in (
            "Anfrage angenommen",
            "peter hat den Versand bestätigt",
            "Dein Versand wurde bestätigt",
            "Du hast den Empfang bestätigt",
            "peter hat den Empfang bestätigt",
            "Trade abgeschlossen",
        ):
            self.assertEqual(timeline.count(f"<strong>{event}</strong>"), 1)

    def test_timeline_toggle_is_native_ui_only_and_not_persisted(self):
        joined = "\n".join(
            self._read(name)
            for name in (
                "trade-running.html",
                "trade-running-timeline.html",
                "trade-completed.html",
                "trade-completed-timeline.html",
            )
        ).lower()
        self.assertEqual(joined.count('<details class="uif005a-timeline'), 4)
        self.assertNotIn("localstorage", joined)
        self.assertNotIn("sessionstorage", joined)
        self.assertNotIn("method=", joined)
        self.assertNotIn("action=", joined)

    def test_completed_state_uses_success_semantics_and_visual_rating(self):
        html = self._read("trade-completed.html")
        self.assertIn("Trade abgeschlossen", html)
        self.assertIn("is-success", html)
        self.assertIn("peter bewerten", html)
        self.assertIn("keine Bewertung gespeichert", html)
        self.assertNotIn("Dieser Trade kann noch nicht bewertet werden", html)
        self.assertNotIn("method=", html.lower())
        self.assertNotIn("action=", html.lower())

    def test_concept_avoids_old_paper_language_and_blue_status(self):
        joined = "\n".join(
            self._read(name)
            for name in (
                "trade-running.html",
                "trade-running-timeline.html",
                "trade-completed.html",
                "trade-completed-timeline.html",
                "trade-detail-concept.css",
            )
        ).lower()
        for forbidden in ("kolleg", "notebook", "handwriting", "#2563eb"):
            self.assertNotIn(forbidden, joined)

    def test_css_keeps_mobile_box_model_and_global_bottom_nav(self):
        css = self._read("trade-detail-concept.css")
        self.assertIn("box-sizing:border-box", css)
        self.assertIn("width:min(100% - 24px, 900px)", css)
        self.assertIn("@media (max-width:350px)", css)
        self.assertIn("@media (min-width:900px)", css)
        self.assertIn(".bottom-nav:not(.album-bottom-nav)", css)
        self.assertIn(":has(.uif005a-timeline[open])", css)


if __name__ == "__main__":
    unittest.main()
