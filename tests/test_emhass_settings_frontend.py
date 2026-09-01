from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class EmhassSettingsFrontendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v041-emhass-settings.js").read_text(
            encoding="utf-8"
        )

    def test_active_panel_loads_enhanced_emhass_settings_entrypoint(self) -> None:
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        v048 = (FRONTEND / "gw-energy-pilot-v048.js").read_text(encoding="utf-8")
        v047 = (FRONTEND / "gw-energy-pilot-v047.js").read_text(encoding="utf-8")
        v046 = (FRONTEND / "gw-energy-pilot-v046.js").read_text(encoding="utf-8")
        v045 = (FRONTEND / "gw-energy-pilot-v045.js").read_text(encoding="utf-8")
        release = (FRONTEND / "gw-energy-pilot-v044.js").read_text(encoding="utf-8")
        v043 = (FRONTEND / "gw-energy-pilot-v043.js").read_text(encoding="utf-8")
        v042 = (FRONTEND / "gw-energy-pilot-v042.js").read_text(encoding="utf-8")
        self.assertIn("gw-energy-pilot-v110.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1", init_source)
        self.assertIn('import "./gw-energy-pilot-v047.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1"', v048)
        self.assertIn('import "./gw-energy-pilot-v046.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1"', v047)
        self.assertIn('import "./gw-energy-pilot-v045.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1"', v046)
        self.assertIn('import "./gw-energy-pilot-v044.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1"', v045)
        self.assertIn(
            'import "./gw-energy-pilot-v043.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1"',
            release,
        )
        self.assertIn('const VERSION = "0.44"', release)
        self.assertIn('import "./gw-energy-pilot-v042.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1"', v043)
        self.assertIn('import "./gw-energy-pilot-v041-emhass-settings.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1"', v042)
        self.assertIn('import "./gw-energy-pilot-v041.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1"', self.source)
        self.assertIn("__epV041EmhassSettingsInstalled", self.source)

    def test_emhass_fields_are_grouped_without_changing_setting_keys(self) -> None:
        expected_keys = {
            "enable_emhass_orchestrator",
            "emhass_url",
            "emhass_optimization_interval",
            "emhass_soc_final_pct",
            "emhass_fallback_load",
            "p_batt_entity",
            "p_grid_entity",
            "optim_status_entity",
            "optim_required_state",
            "use_nordpool_prices",
            "optimize_on_tomorrow_prices",
            "nordpool_area",
            "nordpool_currency",
            "buy_price_adder",
            "sell_price_deduction",
        }
        for key in expected_keys:
            with self.subTest(key=key):
                self.assertIn(f'"{key}"', self.source)

        self.assertIn("1. Connection & planning", self.source)
        self.assertIn("2. Outputs", self.source)
        self.assertIn("3. Price settings", self.source)
        self.assertIn("4. EMHASS configuration check", self.source)

    def test_configuration_check_uses_existing_sync_api_payload(self) -> None:
        self.assertIn("panel.__epV028Sync", self.source)
        self.assertIn("managed_values", self.source)
        self.assertIn("item.current", self.source)
        self.assertIn("item.required", self.source)
        self.assertIn("item.synchronized", self.source)
        self.assertIn("EMHASS stored", self.source)
        self.assertIn("EMHASS opgeslagen", self.source)
        self.assertNotIn("callWS(", self.source)

    def test_existing_sync_and_defaults_actions_are_reused(self) -> None:
        self.assertIn('form.querySelector(".ep-v028-sync-tools")', self.source)
        self.assertIn("const defaults = buttons[0]", self.source)
        self.assertIn("const sync = buttons[1]", self.source)
        self.assertIn("actions.prepend(controls.defaults)", self.source)
        self.assertIn("buildSummary(panel, form, current, controls.sync)", self.source)

    def test_settings_renderer_supports_bounded_interval_select(self) -> None:
        settings_source = (
            FRONTEND / "gw-energy-pilot-settings-v016.js"
        ).read_text(encoding="utf-8")
        self.assertIn('field.type === "select"', settings_source)
        self.assertIn('<select class="ep-v016-input"', settings_source)

    def test_emhass_only_values_are_not_falsely_attached_to_energypilot_fields(self) -> None:
        self.assertIn("The editable fields are EnergyPilot settings", self.source)
        self.assertIn("De bewerkbare velden zijn EnergyPilot-instellingen", self.source)
        self.assertIn("EnergyPilot saved", self.source)
        self.assertIn("EnergyPilot opgeslagen", self.source)
        self.assertIn("Expected EMHASS publication", self.source)
        self.assertIn("Verwachte EMHASS-publicatie", self.source)


if __name__ == "__main__":
    unittest.main()
