#!/usr/bin/env python3
"""Run the shared frontend stability matrix against v0.46."""

from __future__ import annotations

import test_frontend_stability_v045  # noqa: F401 - installs v0.45 hooks
import test_frontend_stability as stability


stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v046"
stability.EXPECTED_ENTRYPOINT = "v046"


if __name__ == "__main__":
    raise SystemExit(stability.main())
