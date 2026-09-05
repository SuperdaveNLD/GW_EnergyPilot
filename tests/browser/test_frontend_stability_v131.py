#!/usr/bin/env python3
"""Run the v1.3.0-beta.3 frontend regression matrix."""

from __future__ import annotations

import test_frontend_stability as stability


if __name__ == "__main__":
    stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v131"
    stability.EXPECTED_ENTRYPOINT = "v131"
    raise SystemExit(stability.main())
