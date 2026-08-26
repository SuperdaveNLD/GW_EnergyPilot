from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FrontendInteractionDocumentationTests(unittest.TestCase):
    def test_interaction_and_flow_contract_is_documented(self) -> None:
        source = (ROOT / "docs" / "FRONTEND_INTERACTION.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("do not use `pointerdown`/`pointerup` locks", source)
        self.assertIn("do not call `setPointerCapture`", source)
        self.assertIn("one delegated `click` listener", source)
        self.assertIn("negative import, positive export", source)
        self.assertIn("negative charge, positive discharge", source)
        self.assertIn("final animation-direction authority", source)


if __name__ == "__main__":
    unittest.main()
