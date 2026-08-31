from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"


class BatterySaverApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (INTEGRATION / "battery_saver_api.py").read_text(encoding="utf-8")

    def test_custom_mode_releases_profile_without_resetting_emhass(self) -> None:
        source = self.source
        self.assertIn('CUSTOM_MODE = "custom"', source)
        self.assertIn(
            "SELECTABLE_MODES: tuple[str, ...] = (*BATTERY_SAVER_MODES, CUSTOM_MODE)",
            source,
        )
        self.assertIn(
            "mode = None if requested_mode == CUSTOM_MODE else normalize_battery_saver_mode(",
            source,
        )

        custom_start = source.index("    if mode is None:\n")
        custom_end = source.index("    hass.config_entries.async_update_entry", custom_start)
        custom_branch = source[custom_start:custom_end]
        self.assertIn("new_options.pop(CONF_BATTERY_SAVER_MODE, None)", custom_branch)
        self.assertNotIn("async_write_emhass_config", custom_branch)
        self.assertNotIn("BATTERY_SAVER_CONFIG_KEYS", custom_branch)

    def test_custom_is_not_blocked_by_managed_profile_constraints(self) -> None:
        source = self.source
        self.assertIn("if mode is not None and number_of_batteries(config) != 1:", source)
        self.assertIn(
            "mode is not None\n        and battery_saver_mode_requires_stress_support(mode)",
            source,
        )

    def test_every_mode_transition_rebuilds_plan_immediately(self) -> None:
        source = self.source
        self.assertIn(
            'await orchestrator.async_optimize(reason="battery_saver_changed")',
            source,
        )
        self.assertIn(
            '"""Select a managed preset or Custom and rebuild the plan immediately."""',
            source,
        )

    def test_failed_transition_rolls_back_options_and_owned_config(self) -> None:
        source = self.source
        failure_start = source.index("    except Exception as err:")
        failure_end = source.index("    # The optimize+initial publish", failure_start)
        rollback = source[failure_start:failure_end]

        self.assertIn(
            "hass.config_entries.async_update_entry(entry, options=old_options)",
            rollback,
        )
        self.assertIn("orchestrator.last_battery_saver_profile = previous_profile", rollback)
        self.assertIn(
            "orchestrator.last_effective_soc_final = previous_effective_soc",
            rollback,
        )
        self.assertIn("_async_restore_battery_saver_config(", rollback)
        self.assertIn("async_set_goodwe_minimum_soc(", rollback)

    def test_managed_profile_writes_verified_goodwe_minimum_before_optimization(self) -> None:
        source = self.source
        write = source.index("await async_set_goodwe_minimum_soc(entry, requested_minimum)")
        option = source.index("hass.config_entries.async_update_entry(entry, options=new_options)")
        optimize = source.index('await orchestrator.async_optimize(reason="battery_saver_changed")')
        self.assertLess(write, option)
        self.assertLess(option, optimize)
        self.assertIn(
            "new_options[CONF_BATTERY_SAVER_SOC_LIMITS_MANAGED] = True",
            source,
        )

    def test_dashboard_settings_preserve_managed_soc_ownership(self) -> None:
        settings = (INTEGRATION / "settings_api.py").read_text(encoding="utf-8")
        generic_start = settings.index("        form_values = _options_for_form")
        generic_end = settings.index(
            "    require_restart = await _async_reload_entry"
        )
        generic_save = settings[generic_start:generic_end]

        self.assertIn(
            "BATTERY_SAVER_OPTION_KEYS = (\n"
            "    CONF_BATTERY_SAVER_MODE,\n"
            "    CONF_BATTERY_SAVER_SOC_LIMITS_MANAGED,\n"
            ")",
            settings,
        )
        self.assertIn(
            "preserved_battery_saver = {\n"
            "            key: form_values.pop(key)\n"
            "            for key in BATTERY_SAVER_OPTION_KEYS\n"
            "            if key in form_values\n"
            "        }",
            generic_save,
        )
        self.assertIn(
            "stored_options.update(preserved_battery_saver)", generic_save
        )

    def test_custom_cost_editor_uses_one_validated_transaction(self) -> None:
        source = self.source
        self.assertIn(
            'vol.Required("type"): "gw_energypilot/battery_saver/custom_set"',
            source,
        )
        self.assertIn('vol.Required("values"): CUSTOM_BATTERY_COST_SCHEMA', source)
        self.assertIn("updates = custom_battery_cost_updates(msg[\"values\"])", source)
        self.assertIn("if number_of_batteries(config) != 1:", source)
        self.assertIn("updated_config = dict(config)", source)
        self.assertIn("updated_config.update(updates)", source)
        self.assertIn(
            'await orchestrator.async_optimize(reason="battery_saver_custom_changed")',
            source,
        )

    def test_failed_custom_cost_apply_restores_profile_and_all_owned_fields(self) -> None:
        source = self.source
        start = source.index("async def websocket_set_custom_battery_costs(")
        end = source.index("\n\n@callback", start)
        custom = source[start:end]
        failure_start = custom.index("    except Exception as err:")
        failure_end = custom.index("    try:\n        refreshed_config", failure_start)
        rollback = custom[failure_start:failure_end]

        self.assertIn(
            "hass.config_entries.async_update_entry(entry, options=old_options)",
            rollback,
        )
        self.assertIn("orchestrator.last_battery_saver_profile = previous_profile", rollback)
        self.assertIn(
            "orchestrator.last_effective_soc_final = previous_effective_soc",
            rollback,
        )
        self.assertIn("_async_restore_battery_saver_config(", rollback)


if __name__ == "__main__":
    unittest.main()
