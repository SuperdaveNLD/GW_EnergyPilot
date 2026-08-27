#!/usr/bin/env python3
"""Real-browser frontend stability diagnostics and regressions."""

from __future__ import annotations

import contextlib
import http.server
import json
import os
import socket
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from playwright.sync_api import BrowserType, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HARNESS = "/tests/browser/frontend_harness.html"


@dataclass(frozen=True)
class Profile:
    name: str
    engine: str
    width: int
    height: int
    mobile: bool
    touch: bool


PROFILES = (
    Profile("desktop-chromium", "chromium", 1440, 900, False, False),
    Profile("ipad-webkit", "webkit", 834, 1112, True, True),
    Profile("iphone-webkit", "webkit", 390, 844, True, True),
)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


@contextlib.contextmanager
def static_server() -> Iterator[str]:
    class RootedHandler(QuietHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(ROOT), **kwargs)

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), RootedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def browser_type(playwright: object, name: str) -> BrowserType:
    return getattr(playwright, name)


def animation_summary(page: Page) -> dict[str, int]:
    return page.evaluate(
        """
        () => {
          const panel = window.__epPanel;
          const root = panel.shadowRoot;
          let animations = 0;
          let transitions = 0;
          let animatedElements = 0;
          for (const element of root.querySelectorAll('*')) {
            const style = getComputedStyle(element);
            const animationNames = style.animationName.split(',').map((item) => item.trim());
            const animationDurations = style.animationDuration.split(',').map((item) => item.trim());
            const transitionDurations = style.transitionDuration.split(',').map((item) => item.trim());
            const hasAnimation = animationNames.some((name) => name && name !== 'none') &&
              animationDurations.some((duration) => duration !== '0s');
            const hasTransition = transitionDurations.some((duration) => duration !== '0s');
            if (hasAnimation) animations += 1;
            if (hasTransition) transitions += 1;
            if (hasAnimation || hasTransition) animatedElements += 1;
          }
          return { animations, transitions, animatedElements };
        }
        """
    )


def exercise_profile(page: Page, profile: Profile) -> dict[str, object]:
    page.goto(page.url or "about:blank")
    page.goto(f"{page.context._options.get('base_url', '')}{HARNESS}" if page.context._options.get('base_url') else HARNESS)
    page.evaluate("window.__epReady")
    page.wait_for_timeout(600)

    initial = page.evaluate(
        """
        () => {
          const scroller = window.__epScroller;
          window.__epInitialMain = window.__epPanel.shadowRoot.querySelector('main');
          const max = scroller.scrollHeight - scroller.clientHeight;
          scroller.scrollTop = Math.max(0, Math.round(max * 0.55));
          return {
            scrollTop: scroller.scrollTop,
            scrollHeight: scroller.scrollHeight,
            clientHeight: scroller.clientHeight,
            max,
            cards: window.__epPanel.shadowRoot.querySelectorAll('[data-ep-card]').length,
            buttons: window.__epPanel.shadowRoot.querySelectorAll('button').length,
          };
        }
        """
    )
    page.wait_for_timeout(100)

    idle_before = page.evaluate("window.__epScroller.scrollTop")
    page.evaluate("window.__epTelemetryBurst(35, 4)")
    page.wait_for_timeout(900)
    idle_after = page.evaluate("window.__epScroller.scrollTop")
    main_stable = page.evaluate(
        "window.__epInitialMain === window.__epPanel.shadowRoot.querySelector('main')"
    )

    motion = page.evaluate(
        """
        async () => {
          const scroller = window.__epScroller;
          const start = scroller.scrollTop;
          const target = Math.min(
            scroller.scrollHeight - scroller.clientHeight,
            start + Math.max(500, scroller.clientHeight * 0.75)
          );
          const samples = [];
          const telemetry = window.__epTelemetryBurst(70, 4);
          const steps = 50;
          for (let index = 1; index <= steps; index += 1) {
            scroller.scrollTop = start + ((target - start) * index / steps);
            samples.push(scroller.scrollTop);
            await new Promise((resolve) => setTimeout(resolve, 12));
          }
          await telemetry;
          await new Promise((resolve) => setTimeout(resolve, 850));
          return {
            start,
            target,
            final: scroller.scrollTop,
            min: Math.min(...samples),
            max: Math.max(...samples),
            backwards: samples.reduce((count, value, index) =>
              index > 0 && value + 2 < samples[index - 1] ? count + 1 : count, 0),
          };
        }
        """
    )

    controls = page.evaluate(
        """
        async () => {
          const root = window.__epPanel.shadowRoot;
          const result = {};
          const layout = root.querySelector('.ep-layout-button');
          layout?.click();
          await new Promise((resolve) => setTimeout(resolve, 100));
          result.menuOpen = Boolean(root.querySelector('.ep-layout-menu'));
          root.querySelector('.ep-menu-close')?.click();
          await new Promise((resolve) => setTimeout(resolve, 100));
          result.menuClosed = !root.querySelector('.ep-layout-menu');
          const auto = root.querySelector('#auto-toggle');
          result.autoPresent = Boolean(auto);
          if (auto) {
            const before = auto.textContent.trim();
            auto.click();
            await new Promise((resolve) => setTimeout(resolve, 200));
            const current = root.querySelector('#auto-toggle');
            result.autoChanged = Boolean(current && current.textContent.trim() !== before);
          }
          return result;
        }
        """
    )

    return {
        "profile": profile.name,
        "initial": initial,
        "idle_before": idle_before,
        "idle_after": idle_after,
        "idle_delta": idle_after - idle_before,
        "main_stable": main_stable,
        "motion": motion,
        "controls": controls,
        "animation": animation_summary(page),
        "errors": page.evaluate("window.__epErrors"),
        "unknown_ws": page.evaluate("Array.from(window.__epUnknownWsTypes).sort()"),
    }


def main() -> int:
    results: list[dict[str, object]] = []
    failures: list[str] = []
    with static_server() as base_url, sync_playwright() as playwright:
        for profile in PROFILES:
            engine = browser_type(playwright, profile.engine)
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
            try:
                result = exercise_profile(page, profile)
                result["page_errors"] = page_errors
                results.append(result)
                if result["initial"]["max"] < 500:
                    failures.append(f"{profile.name}: harness is not sufficiently scrollable")
                if result["controls"]["menuOpen"] is not True:
                    failures.append(f"{profile.name}: dashboard menu did not open")
                if result["controls"]["menuClosed"] is not True:
                    failures.append(f"{profile.name}: dashboard menu did not close")
                if result["errors"] or page_errors:
                    failures.append(f"{profile.name}: JavaScript errors were reported")
            finally:
                context.close()
                browser.close()

    print(json.dumps({"results": results, "failures": failures}, indent=2, sort_keys=True))
    if failures:
        print("Browser diagnostic failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
