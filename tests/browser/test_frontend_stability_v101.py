"""Run the v1.0.1-beta.1 frontend regression matrix."""

from __future__ import annotations

import test_frontend_stability as stability


if __name__ == "__main__":
    stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v101"
    stability.EXPECTED_ENTRYPOINT = "v101"
    raise SystemExit(stability.main())
