#!/usr/bin/env python3
"""Run the shared frontend stability matrix against v0.44."""

from __future__ import annotations

import test_frontend_stability_v041  # noqa: F401 - installs the structural test hook
import test_frontend_stability as stability


stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v044"
stability.EXPECTED_ENTRYPOINT = "v044"


if __name__ == "__main__":
    raise SystemExit(stability.main())
