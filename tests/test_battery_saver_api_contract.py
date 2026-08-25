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
            "mode is not None\n        and mode != MODE_MAD_STEVE",
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


if __name__ == "__main__":
    unittest.main()
