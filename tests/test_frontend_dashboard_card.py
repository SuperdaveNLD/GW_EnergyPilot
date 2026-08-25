from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "gw_energypilot" / "frontend"


class FrontendDashboardCardTests(unittest.TestCase):
    def test_battery_plan_installer_is_idempotent_and_refreshable(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js").read_text(
            encoding="utf-8"
        )
        start = source.index("function installEnhancedCard")
        end = source.index("await customElements.whenDefined", start)
        installer = source[start:end]

        duplicate_guard = 'querySelectorAll(".ep-v027-battery-plan-card")'
        card_creation = 'document.createElement("article")'
        self.assertIn(duplicate_guard, installer)
        self.assertIn("existingCards.slice(1)", installer)
        self.assertIn("duplicate.remove()", installer)
        self.assertIn("dataset.epRenderKey", installer)
        self.assertIn("existingCard.replaceWith(card)", installer)
        self.assertLess(installer.index(duplicate_guard), installer.index(card_creation))

    def test_battery_plan_change_bypasses_chart_cache(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("function activePlanChanged", source)
        self.assertIn("state.last_updated !== plan.last_updated", source)
        self.assertIn("activePlanChanged(panel, data)", source)
        self.assertIn("loadChartData(panel, true)", source)

    def test_release_layer_reconciles_existing_duplicate_cards(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v030.js").read_text(encoding="utf-8")

        self.assertIn("function reconcileBatteryPlanCards", source)
        self.assertIn(".ep-v031-card-windowbar, .ep-v028-window-controls", source)
        self.assertIn("if (card !== canonical) card.remove()", source)
        self.assertIn("reconcileBatteryPlanCards(root)", source)
        self.assertIn("__epV030RenderInstalled", source)


if __name__ == "__main__":
    unittest.main()
