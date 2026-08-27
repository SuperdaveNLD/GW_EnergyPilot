#!/usr/bin/env python3
"""Verify that v0.41.1 Optimize now never rebuilds the touched dashboard."""

from __future__ import annotations

import json
from pathlib import Path
import re

from playwright.sync_api import Error as PlaywrightError, Page, sync_playwright

import test_frontend_stability as stability


HARNESS = "/tests/browser/frontend_harness.html?entry=v041"
ACTIVE_MODULE_REQUEST = re.compile(
    r".*/gw-energy-pilot-v041\.js\?browser-harness=1$"
)
ACTIVE_MODULE_SHIM = (
    'import "/custom_components/gw_energypilot/frontend/'
    'gw-energy-pilot-v0411.js?browser-harness=1";\n'
)


def load_active_hotfix(page: Page) -> None:
    """Make the shared v0.41 harness load the active v0.41.1 wrapper."""

    def fulfill(route) -> None:
        route.fulfill(
            status=200,
            content_type="application/javascript",
            body=ACTIVE_MODULE_SHIM,
        )

    page.route(ACTIVE_MODULE_REQUEST, fulfill)


def exercise_optimize(page: Page, profile: stability.Profile) -> dict[str, object]:
    """Press a visible Optimize control and prove its interaction DOM survives."""
    page.goto(HARNESS, wait_until="domcontentloaded", timeout=30_000)
    page.evaluate("window.__epReady")
    page.wait_for_function(
        """
        () => {
          const panel = window.__epPanel;
          const root = panel?.shadowRoot;
          const button = root?.querySelector('.ep-optimize-now');
          return Boolean(
            button &&
            button.dataset.epV0411StableOptimize === '1' &&
            root.querySelector('.version')?.textContent.includes('0.41.1') &&
            panel.__epV027BatteryPlanData?.payload &&
            !panel.__epV027BatteryPlanPromise
          );
        }
        """,
        timeout=15_000,
    )

    button = stability.shadow(page, ".ep-optimize-now")
    button.evaluate(
        "node => node.scrollIntoView({block: 'center', inline: 'nearest'})"
    )
    page.wait_for_timeout(180)

    initial = page.evaluate(
        """
        () => {
          const panel = window.__epPanel;
          const root = panel.shadowRoot;
          const scroller = window.__epScroller;
          const optimizeId = panel._entityId('optimize_now');
          const revision = Number(
            window.__epHass.states[optimizeId]?.attributes?.plan_revision || 0
          );
          const optimize = root.querySelector('.ep-optimize-now');
          const rect = optimize?.getBoundingClientRect();

          window.__epOptimizeIdentity = {
            main: root.querySelector('main'),
            optimize,
            layout: root.querySelector('.ep-layout-button'),
            automatic: root.querySelector('#auto-toggle'),
            strategy: root.querySelector('[data-ep-v038-profile="mad_steve"]'),
          };
          window.__epOptimizeRenderCount = 0;
          const originalRender = panel._render;
          panel._render = function v0411OptimizeRenderProbe(...args) {
            window.__epOptimizeRenderCount += 1;
            return originalRender.apply(this, args);
          };

          return {
            maximum: scroller.scrollHeight - scroller.clientHeight,
            scrollTop: scroller.scrollTop,
            revision,
            buttonVisible: Boolean(
              rect &&
              rect.bottom > 0 &&
              rect.top < scroller.clientHeight
            ),
          };
        }
        """
    )

    if profile.touch:
        button.tap(timeout=5_000)
    else:
        button.click(timeout=5_000)
    page.wait_for_function(
        """
        previousRevision => {
          const panel = window.__epPanel;
          const root = panel.shadowRoot;
          const optimizeId = panel._entityId('optimize_now');
          const revision = Number(
            window.__epHass.states[optimizeId]?.attributes?.plan_revision || 0
          );
          const chartRevision = Number(
            panel.__epV027BatteryPlanData?.payload?.plan_revision || 0
          );
          const button = root.querySelector('.ep-optimize-now');
          return Boolean(
            revision === previousRevision + 1 &&
            chartRevision === revision &&
            !panel.__epV027BatteryPlanPromise &&
            button &&
            button.getAttribute('aria-busy') === 'false' &&
            !button.disabled
          );
        }
        """,
        arg=initial["revision"],
        timeout=15_000,
    )
    page.wait_for_timeout(350)

    result = page.evaluate(
        """
        async initial => {
          const panel = window.__epPanel;
          const root = panel.shadowRoot;
          const scroller = window.__epScroller;
          const afterOptimize = scroller.scrollTop;
          const maximum = scroller.scrollHeight - scroller.clientHeight;
          const distance = Math.max(320, Math.round(scroller.clientHeight * 0.45));
          const downSpace = maximum - afterOptimize;
          const upSpace = afterOptimize;
          const probeTarget = downSpace >= 250
            ? Math.min(maximum, afterOptimize + distance)
            : Math.max(0, afterOptimize - Math.min(distance, upSpace));
          const probeDistance = Math.abs(probeTarget - afterOptimize);
          scroller.scrollTop = probeTarget;
          await new Promise((resolve) => setTimeout(resolve, 180));
          const optimizeId = panel._entityId('optimize_now');
          const button = root.querySelector('.ep-optimize-now');
          return {
            maximum,
            renderCount: window.__epOptimizeRenderCount,
            mainStable: window.__epOptimizeIdentity.main === root.querySelector('main'),
            optimizeStable:
              window.__epOptimizeIdentity.optimize === root.querySelector('.ep-optimize-now'),
            layoutStable:
              window.__epOptimizeIdentity.layout === root.querySelector('.ep-layout-button'),
            automaticStable:
              window.__epOptimizeIdentity.automatic === root.querySelector('#auto-toggle'),
            strategyStable:
              window.__epOptimizeIdentity.strategy === root.querySelector(
                '[data-ep-v038-profile="mad_steve"]'
              ),
            scrollBefore: initial.scrollTop,
            scrollAfterOptimize: afterOptimize,
            probeTarget,
            probeDistance,
            scrollAfterProbe: scroller.scrollTop,
            revision: Number(
              window.__epHass.states[optimizeId]?.attributes?.plan_revision || 0
            ),
            buttonBusy: button?.getAttribute('aria-busy'),
            buttonDisabled: Boolean(button?.disabled),
            marker: button?.dataset?.epV0411StableOptimize || '',
            version: root.querySelector('.version')?.textContent || '',
            errors: window.__epErrors,
            unknownWs: Array.from(window.__epUnknownWsTypes).sort(),
          };
        }
        """,
        initial,
    )
    return {"initial": initial, "result": result}


def failures_for(
    profile: stability.Profile,
    payload: dict[str, object],
    page_errors: list[str],
) -> list[str]:
    """Return deterministic failures for one browser profile."""
    failures: list[str] = []
    name = profile.name
    initial = payload["initial"]
    result = payload["result"]

    if initial["maximum"] < 500:
        failures.append(f"{name}: harness is not sufficiently scrollable")
    if initial["buttonVisible"] is not True:
        failures.append(f"{name}: Optimize control was not visible before activation")
    if result["renderCount"] != 0:
        failures.append(
            f"{name}: Optimize now triggered {result['renderCount']} complete render(s)"
        )
    for key in (
        "mainStable",
        "optimizeStable",
        "layoutStable",
        "automaticStable",
        "strategyStable",
    ):
        if result[key] is not True:
            failures.append(f"{name}: Optimize now replaced {key}")
    if abs(result["scrollAfterOptimize"] - result["scrollBefore"]) > 5:
        failures.append(
            f"{name}: Optimize now moved scroll by "
            f"{result['scrollAfterOptimize'] - result['scrollBefore']} px"
        )
    if result["probeDistance"] < 200:
        failures.append(f"{name}: no useful post-optimize scroll range remained")
    if abs(result["scrollAfterProbe"] - result["probeTarget"]) > 5:
        failures.append(f"{name}: scrolling stopped working after Optimize now")
    if result["revision"] != initial["revision"] + 1:
        failures.append(f"{name}: Optimize now did not execute exactly once")
    if result["buttonBusy"] != "false" or result["buttonDisabled"] is not False:
        failures.append(f"{name}: Optimize now did not return to an idle state")
    if result["marker"] != "1" or "0.41.1" not in result["version"]:
        failures.append(f"{name}: active v0.41.1 optimize wrapper is missing")
    if result["errors"] or page_errors:
        failures.append(f"{name}: JavaScript errors were reported")
    if result["unknownWs"]:
        failures.append(f"{name}: harness encountered unknown WebSocket calls")
    return failures


def main() -> int:
    """Run the Optimize now regression on desktop, iPad and iPhone engines."""
    results: list[dict[str, object]] = []
    failures: list[str] = []
    with stability.static_server() as base_url, sync_playwright() as playwright:
        for profile in stability.PROFILES:
            engine = stability.browser_type(playwright, profile.engine)
            browser = engine.launch(headless=True)
            context = browser.new_context(
                base_url=base_url,
                viewport={"width": profile.width, "height": profile.height},
                is_mobile=profile.mobile,
                has_touch=profile.touch,
                device_scale_factor=2 if profile.mobile else 1,
                locale="en-US",
            )
            page = context.new_page()
            page_errors: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            load_active_hotfix(page)
            try:
                payload = exercise_optimize(page, profile)
                payload["profile"] = profile.name
                payload["page_errors"] = page_errors
                results.append(payload)
                failures.extend(failures_for(profile, payload, page_errors))
            except PlaywrightError as err:
                results.append(
                    {
                        "profile": profile.name,
                        "fatal_error": str(err),
                        "page_errors": page_errors,
                    }
                )
                failures.append(f"{profile.name}: browser profile aborted: {err}")
            finally:
                context.close()
                browser.close()

    report = {"results": results, "failures": failures}
    print(json.dumps(report, indent=2, sort_keys=True))
    Path("frontend-optimize-results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if failures:
        print("Optimize now browser failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
