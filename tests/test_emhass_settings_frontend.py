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
        self.assertIn("gw-energy-pilot-v131.js?v=1.3.0-beta.3", init_source)
        self.assertIn('import "./gw-energy-pilot-v047.js?v=1.3.0-beta.3"', v048)
        self.assertIn('import "./gw-energy-pilot-v046.js?v=1.3.0-beta.3"', v047)
        self.assertIn('import "./gw-energy-pilot-v045.js?v=1.3.0-beta.3"', v046)
        self.assertIn('import "./gw-energy-pilot-v044.js?v=1.3.0-beta.3"', v045)
        self.assertIn(
            'import "./gw-energy-pilot-v043.js?v=1.3.0-beta.3"',
            release,
        )
        self.assertIn('const VERSION = "0.44"', release)
        self.assertIn('import "./gw-energy-pilot-v042.js?v=1.3.0-beta.3"', v043)
        self.assertIn('import "./gw-energy-pilot-v041-emhass-settings.js?v=1.3.0-beta.3"', v042)
        self.assertIn('import "./gw-energy-pilot-v041.js?v=1.3.0-beta.3"', self.source)
        self.assertIn("__epV041EmhassSettingsInstalled", self.source)

    def test_emhass_fields_are_grouped_without_changing_setting_keys(self) -> None:
        expected_keys = {
            "enable_emhass_orchestrator",
            "emhass_url",
            "emhass_optimization_interval",
            "emhass_soc_final_pct",
            "emhass_fallback_load",
            "emhass_custom_load_forecast",
            "emhass_custom_load_power",
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

    def test_custom_load_power_is_visible_only_in_custom_mode(self) -> None:
        self.assertIn("syncCustomLoadForecastField(form)", self.source)
        self.assertIn("field.hidden = !custom", self.source)
        self.assertIn("power.disabled = !custom", self.source)
        self.assertIn('badge.textContent = custom ? "CUSTOM" : "AUTO"', self.source)
        self.assertIn(
            'customLoadToggle.addEventListener("change"',
            self.source,
        )

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

    def test_header_has_localized_native_user_guide_link(self) -> None:
        settings_source = (
            FRONTEND / "gw-energy-pilot-settings-v016.js"
        ).read_text(encoding="utf-8")
        self.assertIn("function installHelpButton(panel, root)", settings_source)
        self.assertIn('link.className = "ep-v016-help-button"', settings_source)
        self.assertIn('link.target = "_blank"', settings_source)
        self.assertIn('link.rel = "noopener noreferrer"', settings_source)
        self.assertIn("docs/USER_GUIDE.md", settings_source)
        self.assertIn("docs/HANDLEIDING_NL.md", settings_source)
        self.assertIn("HELP_COPY[language]", settings_source)
        self.assertIn("installHelpButton(this, root)", settings_source)

        # Help is navigation only: no Home Assistant or hardware action path.
        helper = settings_source[
            settings_source.index("function installHelpButton") :
            settings_source.index("function fieldValue")
        ]
        self.assertNotIn("callService", helper)
        self.assertNotIn("callWS", helper)
        self.assertNotIn("_queueRender", helper)

    def test_emhass_only_values_are_not_falsely_attached_to_energypilot_fields(self) -> None:
        self.assertIn("The editable fields are EnergyPilot settings", self.source)
        self.assertIn("De bewerkbare velden zijn EnergyPilot-instellingen", self.source)
        self.assertIn("EnergyPilot saved", self.source)
        self.assertIn("EnergyPilot opgeslagen", self.source)
        self.assertIn("Expected EMHASS publication", self.source)
        self.assertIn("Verwachte EMHASS-publicatie", self.source)


if __name__ == "__main__":
    unittest.main()
