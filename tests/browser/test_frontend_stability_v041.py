#!/usr/bin/env python3
"""Run the shared browser stability matrix against the v0.41 entrypoint."""

from __future__ import annotations

import test_frontend_stability as stability

stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v041"
stability.EXPECTED_ENTRYPOINT = "v041"

if __name__ == "__main__":
    raise SystemExit(stability.main())
