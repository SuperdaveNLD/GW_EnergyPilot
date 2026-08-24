"""Tests for EnergyPilot signed grid-power integration."""

from __future__ import annotations

import math
import unittest

from custom_components.gw_energypilot.accounting_power import integrate_signed_power


class SignedPowerAccountingTests(unittest.TestCase):
    def test_constant_import(self):
        imported, exported = integrate_signed_power(-3600, -3600, 10)
        self.assertAlmostEqual(imported, 0.01, places=9)
        self.assertEqual(exported, 0.0)

    def test_constant_export(self):
        imported, exported = integrate_signed_power(1800, 1800, 20)
        self.assertEqual(imported, 0.0)
        self.assertAlmostEqual(exported, 0.01, places=9)

    def test_import_to_export_crossing_does_not_cancel(self):
        imported, exported = integrate_signed_power(-1000, 1000, 10)
        expected = 2500 / 3_600_000
        self.assertAlmostEqual(imported, expected, places=12)
        self.assertAlmostEqual(exported, expected, places=12)

    def test_asymmetric_zero_crossing(self):
        imported, exported = integrate_signed_power(-2000, 1000, 12)
        self.assertAlmostEqual(imported, 8000 / 3_600_000, places=12)
        self.assertAlmostEqual(exported, 2000 / 3_600_000, places=12)

    def test_invalid_intervals_add_no_energy(self):
        self.assertEqual(integrate_signed_power(1000, 1000, 0), (0.0, 0.0))
        self.assertEqual(
            integrate_signed_power(math.nan, 1000, 10),
            (0.0, 0.0),
        )


if __name__ == "__main__":
    unittest.main()
