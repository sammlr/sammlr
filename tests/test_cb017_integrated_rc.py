from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STYLE_PATH = PROJECT_ROOT / "App" / "static" / "style.css"


class IntegratedClosedBetaRcTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = STYLE_PATH.read_text(encoding="utf-8")

    def test_mobile_full_width_cards_use_border_box(self):
        component_rule = self.css.split(
            ".s31-product-page :where(.page-title,.card,.profile-card,.album-card,",
            1,
        )[1].split("}", 1)[0]
        self.assertIn(".album-quick-card", component_rule)
        self.assertIn("box-sizing:border-box", component_rule)
        self.assertIn("min-width:0", component_rule)

    def test_mobile_album_statistics_grid_can_shrink_inside_390px_viewport(self):
        s31_css = self.css.split(
            "/* S31 – global product workflows on the S30 design foundation */",
            1,
        )[1].split("/* UIF-001", 1)[0]
        mobile = s31_css.rsplit("@media (max-width:430px)", 1)[1].split(
            "@media (max-width:390px)", 1
        )[0]
        self.assertIn(".s31-product-page .stats", mobile)
        self.assertIn("grid-template-columns:repeat(2, minmax(0,1fr))", mobile)
        self.assertIn(".s31-product-page .stat", mobile)
        self.assertIn("box-sizing:border-box", mobile)
        self.assertIn("min-width:0", mobile)


if __name__ == "__main__":
    unittest.main()
