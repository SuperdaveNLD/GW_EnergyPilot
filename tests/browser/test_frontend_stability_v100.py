"""Run the v1.0.0 stable frontend regression matrix."""

from __future__ import annotations

import test_frontend_stability as stability


if __name__ == "__main__":
    stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v100"
    stability.EXPECTED_ENTRYPOINT = "v100"
    raise SystemExit(stability.main())
