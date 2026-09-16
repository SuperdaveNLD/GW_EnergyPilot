#!/usr/bin/env python3
"""Run the historical v1.3.0-beta.1 frontend regression matrix."""

from __future__ import annotations

import test_frontend_stability_v110  # noqa: F401 - retains stable release coverage
import test_frontend_stability as stability


if __name__ == "__main__":
    stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v130"
    stability.EXPECTED_ENTRYPOINT = "v130"
    raise SystemExit(stability.main())
