#!/usr/bin/env python3
"""Run the shared frontend stability matrix against v0.51."""

from __future__ import annotations

import test_frontend_stability_v050  # noqa: F401 - installs inherited hooks
import test_frontend_stability as stability


stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v051"
stability.EXPECTED_ENTRYPOINT = "v051"


if __name__ == "__main__":
    raise SystemExit(stability.main())
