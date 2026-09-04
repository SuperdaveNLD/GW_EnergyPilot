from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UserGuideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.english = (ROOT / "docs" / "USER_GUIDE.md").read_text(
            encoding="utf-8"
        )
        self.dutch = (ROOT / "docs" / "HANDLEIDING_NL.md").read_text(
            encoding="utf-8"
        )

    def test_readme_surfaces_both_user_guides(self) -> None:
        self.assertIn("[English user guide](docs/USER_GUIDE.md)", self.readme)
        self.assertIn("[Nederlandse handleiding](docs/HANDLEIDING_NL.md)", self.readme)

    def test_guides_cover_safe_setup_and_daily_use(self) -> None:
        for guide, required in (
            (
                self.english,
                (
                    "## Install and connect",
                    "## Validate the installation safely",
                    "## Dashboard tour",
                    "## Choose an automatic-control strategy",
                    "## Troubleshooting",
                    "Automatic Control OFF",
                ),
            ),
            (
                self.dutch,
                (
                    "## Installeren en verbinden",
                    "## Veilig valideren vóór automatisch regelen",
                    "## Rondleiding door het dashboard",
                    "## Kies een automatische strategie",
                    "## Problemen oplossen",
                    "Automatische regeling UIT",
                ),
            ),
        ):
            for text in required:
                with self.subTest(text=text):
                    self.assertIn(text, guide)

    def test_guides_link_to_each_other(self) -> None:
        self.assertIn("[Nederlandse handleiding](HANDLEIDING_NL.md)", self.english)
        self.assertIn("[English user guide](USER_GUIDE.md)", self.dutch)


if __name__ == "__main__":
    unittest.main()
