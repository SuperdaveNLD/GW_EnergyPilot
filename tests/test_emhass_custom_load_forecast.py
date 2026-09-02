"""Regression coverage for the EMHASS AUTO/CUSTOM load-forecast request body."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
MODULE_PATH = INTEGRATION / "emhass_load_forecast.py"
ORCHESTRATOR_PATH = INTEGRATION / "orchestrator_v031.py"
SPEC = importlib.util.spec_from_file_location("gw_ep_emhass_load_forecast", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
load_forecast = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(load_forecast)


class EMHASSCustomLoadForecastTests(unittest.TestCase):
    def test_one_day_at_fifteen_minutes_is_96_fixed_700_w_steps(self) -> None:
        body = {
            "soc_init": 0.48,
            "soc_final": 0.10,
            "load_power_forecast": {"existing": 1234},
        }

        steps = load_forecast.apply_custom_load_forecast(
            body,
            {"delta_forecast_daily": 1, "optimization_time_step": 15},
            enabled=True,
            power_w=700,
        )

        self.assertEqual(steps, 96)
        self.assertEqual(body["load_power_forecast"], [700] * 96)

    def test_only_load_forecast_is_overridden_in_runtime_request_body(self) -> None:
        body = {
            "soc_init": 0.48,
            "soc_final": 0.10,
            "prediction_horizon": 8,
            "battery_minimum_state_of_charge": 0.05,
            "load_cost_forecast": [0.20] * 8,
            "prod_price_forecast": [0.08] * 8,
            "load_power_forecast": [1234] * 8,
        }
        before = deepcopy(body)

        steps = load_forecast.apply_custom_load_forecast(
            body,
            {"delta_forecast_daily": 2, "optimization_time_step": 30},
            enabled=True,
            power_w=700,
        )

        self.assertEqual(steps, 8)
        self.assertEqual(body["load_power_forecast"], [700] * 8)
        self.assertEqual(
            {key: value for key, value in body.items() if key != "load_power_forecast"},
            {key: value for key, value in before.items() if key != "load_power_forecast"},
        )

    def test_auto_mode_keeps_existing_runtime_body_unchanged(self) -> None:
        body = {"soc_init": 0.48, "load_power_forecast": {"existing": 1234}}
        before = deepcopy(body)

        steps = load_forecast.apply_custom_load_forecast(
            body,
            {"delta_forecast_daily": 1, "optimization_time_step": 15},
            enabled=False,
            power_w=700,
        )

        self.assertIsNone(steps)
        self.assertEqual(body, before)

    def test_two_days_at_thirty_minutes_is_96_steps(self) -> None:
        self.assertEqual(
            load_forecast.forecast_step_count(
                {"delta_forecast_daily": 2, "optimization_time_step": 30},
                {},
            ),
            96,
        )

    def test_invalid_emhass_time_step_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "optimization_time_step"):
            load_forecast.forecast_step_count(
                {"delta_forecast_daily": 1, "optimization_time_step": 0},
                {},
            )

    def test_override_runs_before_request_is_forwarded_to_emhass(self) -> None:
        source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")
        override = source.index("apply_custom_load_forecast(")
        forward = source.index("return await super()._async_post_emhass(")
        self.assertLess(override, forward)


if __name__ == "__main__":
    unittest.main()
