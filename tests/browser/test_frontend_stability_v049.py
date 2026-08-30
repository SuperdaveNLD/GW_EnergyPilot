#!/usr/bin/env python3
"""Run the shared frontend stability matrix against v0.49."""

from __future__ import annotations

import test_frontend_stability_v048  # noqa: F401 - installs inherited hooks
import test_frontend_stability as stability


stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v049"
stability.EXPECTED_ENTRYPOINT = "v049"


if __name__ == "__main__":
    raise SystemExit(stability.main())
