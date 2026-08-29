#!/usr/bin/env python3
"""Run the shared frontend stability matrix against v0.45."""

from __future__ import annotations

import test_frontend_stability_v041  # noqa: F401 - installs the structural test hook
import test_frontend_stability as stability


stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v045"
stability.EXPECTED_ENTRYPOINT = "v045"

exercise_v041_structural_rerender = stability.exercise_structural_rerender


def exercise_structural_rerender(page):
    """Add v0.45 floating-action reachability to the stable structure checks."""
    result = exercise_v041_structural_rerender(page)
    result.update(
        settings_open=False,
        optimize_in_settings=False,
        settings_close=False,
    )
    if result["error"]:
        return result
    try:
        settings = stability.shadow(page, ".ep-v016-settings-button")
        settings.click(timeout=5_000)
        page.wait_for_function(
            "() => Boolean(window.__epPanel.shadowRoot.querySelector('.ep-v016-settings'))",
            timeout=10_000,
        )
        result["settings_open"] = True
        result["optimize_in_settings"] = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const button = root.querySelector('.ep-optimize-now');
              const rect = button?.getBoundingClientRect();
              return Boolean(
                button && button.parentElement === root.querySelector('main') &&
                getComputedStyle(button).position === 'fixed' &&
                rect && rect.width >= 44 && rect.height >= 44 &&
                rect.top >= 0 && rect.left >= 0 &&
                rect.bottom <= innerHeight && rect.right <= innerWidth
              );
            }
            """
        )
        stability.shadow(page, ".ep-v016-back").click(timeout=5_000)
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-v016-settings')",
            timeout=10_000,
        )
        result["settings_close"] = True
    except stability.PlaywrightError as err:
        result["error"] = str(err)
    return result


stability.exercise_structural_rerender = exercise_structural_rerender


if __name__ == "__main__":
    raise SystemExit(stability.main())
