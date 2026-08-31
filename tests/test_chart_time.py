from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "gw_energypilot" / "chart_time.py"
SPEC = importlib.util.spec_from_file_location("gw_energypilot_chart_time", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CHART_TIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHART_TIME)


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ChartTimeTests(unittest.TestCase):
    def test_windows_follow_home_assistant_timezone(self) -> None:
        payload = CHART_TIME.build_chart_time_payload(
            "Europe/Amsterdam",
            now=datetime(2026, 8, 30, 10, 15, tzinfo=UTC),
        )

        self.assertEqual(payload["time_zone"], "Europe/Amsterdam")
        self.assertEqual(payload["now"], "2026-08-30T10:15:00Z")
        self.assertEqual(payload["day_start"], "2026-08-29T22:00:00Z")
        self.assertEqual(payload["day_end"], "2026-08-30T22:00:00Z")
        self.assertEqual(payload["max_end"], "2026-08-31T10:00:00Z")
        self.assertEqual(payload["windows"]["12h"]["start"], "2026-08-30T04:15:00Z")
        self.assertEqual(payload["windows"]["12h"]["end"], "2026-08-30T16:15:00Z")
        self.assertEqual(payload["windows"]["24h"]["start"], payload["day_start"])
        self.assertEqual(payload["windows"]["24h"]["end"], payload["day_end"])
        self.assertEqual(payload["windows"]["36h"]["end"], payload["max_end"])
        self.assertEqual(
            [tick["day_offset"] for tick in payload["windows"]["36h"]["ticks"]],
            [0, 0, 0, 0, 1, 1, 1],
        )

    def test_spring_dst_day_is_fixed_local_day_not_24_elapsed_hours(self) -> None:
        payload = CHART_TIME.build_chart_time_payload(
            "Europe/Amsterdam",
            now=datetime(2026, 3, 29, 1, 30, tzinfo=UTC),
        )

        fixed = payload["windows"]["24h"]
        self.assertEqual(
            instant(fixed["end"]) - instant(fixed["start"]),
            timedelta(hours=23),
        )
        rolling = payload["windows"]["12h"]
        self.assertEqual(
            instant(rolling["end"]) - instant(rolling["start"]),
            timedelta(hours=12),
        )

    def test_autumn_dst_day_is_25_elapsed_hours(self) -> None:
        payload = CHART_TIME.build_chart_time_payload(
            "Europe/Amsterdam",
            now=datetime(2026, 10, 25, 1, 30, tzinfo=UTC),
        )

        fixed = payload["windows"]["24h"]
        self.assertEqual(
            instant(fixed["end"]) - instant(fixed["start"]),
            timedelta(hours=25),
        )

    def test_invalid_timezone_fails_safe_to_utc(self) -> None:
        payload = CHART_TIME.build_chart_time_payload(
            "Invalid/Timezone",
            now=datetime(2026, 8, 30, 10, 15, tzinfo=UTC),
        )

        self.assertEqual(payload["time_zone"], "UTC")
        self.assertEqual(payload["day_start"], "2026-08-30T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
