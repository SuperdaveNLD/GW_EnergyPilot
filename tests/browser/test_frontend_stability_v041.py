#!/usr/bin/env python3
"""Run the shared browser stability matrix against the v0.41 harness."""

from __future__ import annotations

import test_frontend_stability as stability

stability.HARNESS = "/tests/browser/frontend_harness_v041.html"

if __name__ == "__main__":
    raise SystemExit(stability.main())
