from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class PriceAdjustmentPrecisionTests(unittest.TestCase):
    def test_home_assistant_selector_step_stays_supported(self) -> None:
        source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")

        buy_start = source.index("CONF_BUY_PRICE_ADDER")
        sell_start = source.index("CONF_SELL_PRICE_DEDUCTION", buy_start)
        ev_start = source.index("CONF_ENABLE_EV_COORDINATION", sell_start)
        price_schema = source[buy_start:ev_start]

        self.assertNotIn("step=0.0001", price_schema)
        self.assertEqual(price_schema.count("step=0.001"), 2)
        self.assertIn("NumberSelectorMode.BOX", price_schema)

    def test_dashboard_keeps_four_decimal_input_increment(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v029.js").read_text(encoding="utf-8")

        self.assertIn('input.step = "0.0001"', source)
        self.assertIn('"buy_price_adder"', source)
        self.assertIn('"sell_price_deduction"', source)

    def test_settings_api_does_not_round_price_values(self) -> None:
        source = (INTEGRATION / "settings_api.py").read_text(encoding="utf-8")

        self.assertIn('"key": CONF_BUY_PRICE_ADDER', source)
        self.assertIn('"key": CONF_SELL_PRICE_DEDUCTION', source)
        self.assertNotIn("round(values[CONF_BUY_PRICE_ADDER]", source)
        self.assertNotIn("round(values[CONF_SELL_PRICE_DEDUCTION]", source)


if __name__ == "__main__":
    unittest.main()
