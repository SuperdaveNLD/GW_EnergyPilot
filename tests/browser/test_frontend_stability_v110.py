#!/usr/bin/env python3
"""Run the v1.2.0-beta.7 frontend regression matrix."""

from __future__ import annotations

import test_frontend_stability_v101  # noqa: F401 - keeps the historical beta matrix in chain
import test_frontend_stability as stability


if __name__ == "__main__":
    stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v110"
    stability.EXPECTED_ENTRYPOINT = "v110"
    raise SystemExit(stability.main())
