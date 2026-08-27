#!/usr/bin/env python3
"""Run the shared browser stability matrix against the v0.41 entrypoint."""

from __future__ import annotations

import test_frontend_stability as stability

stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v041"
stability.EXPECTED_ENTRYPOINT = "v041"


def exercise_structural_rerender(page):
    """Wait for the deliberate main-node replacement before testing controls."""
    result = {
        "cards": 0,
        "main_rebuilt": False,
        "menu_open": False,
        "menu_close": False,
        "error": None,
    }
    try:
        page.evaluate(
            """
            () => {
              window.__epBeforeNarrowMain = window.__epPanel.shadowRoot.querySelector('main');
              window.__epPanel.narrow = !window.__epPanel.narrow;
            }
            """
        )
        page.wait_for_function(
            """
            () => Boolean(
              window.__epBeforeNarrowMain !== window.__epPanel.shadowRoot.querySelector('main') &&
              window.__epPanel.shadowRoot.querySelector('main[data-ep-v041-stable-dom="1"]') &&
              window.__epPanel.shadowRoot.querySelectorAll('[data-ep-card]').length >= 8
            )
            """,
            timeout=10_000,
        )
        result["cards"] = page.evaluate(
            "window.__epPanel.shadowRoot.querySelectorAll('[data-ep-card]').length"
        )
        result["main_rebuilt"] = page.evaluate(
            "window.__epBeforeNarrowMain !== window.__epPanel.shadowRoot.querySelector('main')"
        )
        menu = stability.open_and_close_menu(page)
        result["menu_open"] = menu["open"]
        result["menu_close"] = menu["close"]
        result["error"] = menu["error"]
    except stability.PlaywrightError as err:
        result["error"] = str(err)
    return result


stability.exercise_structural_rerender = exercise_structural_rerender

if __name__ == "__main__":
    raise SystemExit(stability.main())
