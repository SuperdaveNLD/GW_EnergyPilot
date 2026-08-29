#!/usr/bin/env python3
"""Real-browser desktop, iPad and iPhone frontend stability regressions."""

from __future__ import annotations

import contextlib
import http.server
import json
import socket
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from playwright.sync_api import BrowserType, Error as PlaywrightError, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HARNESS = "/tests/browser/frontend_harness.html"
EXPECTED_ENTRYPOINT: str | None = None
STABLE_ENTRYPOINTS = {"v041", "v042", "v043", "v044", "v045"}


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


def shadow(page: Page, selector: str):
    """Return a locator that pierces the panel's open ShadowRoot."""
    return page.locator("gw-energypilot-panel").locator(selector)


def wait_render_idle(page: Page) -> None:
    """Wait until full-render work and two follow-up paint frames have settled."""
    page.wait_for_function(
        "() => Boolean(window.__epPanel && !window.__epPanel._renderQueued)",
        timeout=5_000,
    )
    page.evaluate(
        """
        () => new Promise((resolve) => requestAnimationFrame(
          () => requestAnimationFrame(resolve)
        ))
        """
    )
    page.wait_for_function(
        "() => !window.__epPanel._renderQueued",
        timeout=5_000,
    )


def activate(page: Page, profile: Profile, selector: str) -> None:
    """Use a real touch sequence for touch profiles and a mouse click otherwise."""
    wait_render_idle(page)
    last_error: PlaywrightError | None = None
    for _attempt in range(3):
        control = shadow(page, selector)
        try:
            control.scroll_into_view_if_needed(timeout=5_000)
            break
        except PlaywrightError as err:
            if "not attached" not in str(err).lower():
                raise
            last_error = err
            wait_render_idle(page)
    else:
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Control did not become available: {selector}")

    control = shadow(page, selector)
    if profile.touch:
        control.tap(timeout=5_000)
    else:
        control.click(timeout=5_000)


def animation_summary(page: Page) -> dict[str, int]:
    return page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          let animations = 0;
          let transitions = 0;
          let animatedElements = 0;
          const active = (style) => {
            const animationNames = style.animationName.split(',').map((item) => item.trim());
            const animationDurations = style.animationDuration.split(',').map((item) => item.trim());
            const transitionDurations = style.transitionDuration.split(',').map((item) => item.trim());
            const hasAnimation = animationNames.some((name) => name && name !== 'none') &&
              animationDurations.some((duration) => duration !== '0s');
            const hasTransition = transitionDurations.some((duration) => duration !== '0s');
            return { hasAnimation, hasTransition };
          };
          for (const element of root.querySelectorAll('*')) {
            let elementActive = false;
            for (const pseudo of [null, '::before', '::after']) {
              const state = active(getComputedStyle(element, pseudo));
              if (state.hasAnimation) animations += 1;
              if (state.hasTransition) transitions += 1;
              elementActive ||= state.hasAnimation || state.hasTransition;
            }
            if (elementActive) animatedElements += 1;
          }
          return { animations, transitions, animatedElements };
        }
        """
    )


def open_and_close_menu(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "open": False,
        "close": False,
        "motion_disabled": False,
        "error": None,
    }
    try:
        page.evaluate("window.__epScroller.scrollTop = 0")
        button = shadow(page, ".ep-layout-button")
        button.scroll_into_view_if_needed(timeout=5_000)
        button.click(timeout=5_000)
        page.wait_for_function(
            "() => Boolean(window.__epPanel.shadowRoot.querySelector('.ep-layout-menu'))",
            timeout=5_000,
        )
        result["open"] = True
        result["motion_disabled"] = page.evaluate(
            """
            () => {
              const input = window.__epPanel.shadowRoot.querySelector('[data-ep-setting="animations"]');
              return Boolean(input && input.disabled && !input.checked);
            }
            """
        )
        close = shadow(page, ".ep-menu-close")
        close.click(timeout=5_000)
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-layout-menu')",
            timeout=5_000,
        )
        result["close"] = True
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_automatic_control(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "present": False,
        "off_changed": False,
        "on_changed": False,
        "main_stable": False,
        "error": None,
    }
    try:
        auto = shadow(page, "#auto-toggle")
        auto.scroll_into_view_if_needed(timeout=5_000)
        result["present"] = auto.count() == 1
        page.evaluate(
            "window.__epAutoMain = window.__epPanel.shadowRoot.querySelector('main')"
        )
        automatic_id = page.evaluate(
            "window.__epPanel._entityId('automatic_control')"
        )
        before = page.evaluate(
            "entityId => window.__epHass.states[entityId]?.state",
            automatic_id,
        )
        auto.click(timeout=5_000)
        page.wait_for_function(
            "([entityId, previous]) => window.__epHass.states[entityId]?.state !== previous",
            arg=[automatic_id, before],
            timeout=5_000,
        )
        after_off = page.evaluate(
            "entityId => window.__epHass.states[entityId]?.state",
            automatic_id,
        )
        result["off_changed"] = before == "on" and after_off == "off"

        auto = shadow(page, "#auto-toggle")
        auto.click(timeout=5_000)
        page.wait_for_function(
            "entityId => window.__epHass.states[entityId]?.state === 'on'",
            arg=automatic_id,
            timeout=5_000,
        )
        result["on_changed"] = True
        result["main_stable"] = page.evaluate(
            "window.__epAutoMain === window.__epPanel.shadowRoot.querySelector('main')"
        )
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_strategy(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "present": False,
        "changed": False,
        "message": "",
        "error": None,
    }
    try:
        page.wait_for_function(
            """
            () => {
              const button = window.__epPanel.shadowRoot.querySelector(
                '[data-ep-v038-profile="mad_steve"]'
              );
              return Boolean(button && !button.disabled);
            }
            """,
            timeout=10_000,
        )
        button = shadow(page, '[data-ep-v038-profile="mad_steve"]')
        result["present"] = button.count() == 1
        button.scroll_into_view_if_needed(timeout=5_000)
        button.click(timeout=5_000)
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-ep-v038-profile="mad_steve"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )
        page.wait_for_function(
            """
            () => Boolean(
              !window.__epPanel.__epV038BatterySaver?.busy &&
              !window.__epPanel.__epV038BatterySaver?.loading
            )
            """,
            timeout=10_000,
        )
        result["changed"] = True
        result["message"] = page.evaluate(
            "window.__epPanel.shadowRoot.querySelector('.ep-v038-message')?.textContent || ''"
        )
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_soc_slider_draft(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "present": False,
        "slider_kept_draft": False,
        "label_kept_draft": False,
        "acknowledged": False,
        "error": None,
    }
    try:
        page.evaluate(
            """
            () => {
              const cache = window.__epPanel.__epV038BatterySaver;
              if (cache?.data) cache.data.managed = false;
              window.__epPanel.__epV041RefreshStrategy?.();
            }
            """
        )
        page.wait_for_function(
            "() => Boolean(window.__epPanel.shadowRoot.querySelector('input[data-ep-v038-soc=\"min\"]'))",
            timeout=10_000,
        )
        measured = page.evaluate(
            """
            async () => {
              const root = window.__epPanel.shadowRoot;
              const slider = root.querySelector('input[data-ep-v038-soc="min"]');
              const label = root.querySelector('[data-ep-v038-soc-value="min"]');
              slider.focus();
              slider.value = "37";
              slider.dispatchEvent(new Event("input", { bubbles: true, composed: true }));

              // Chrome can drop focus when the range input becomes stationary or
              // is briefly disabled for persistence. A telemetry patch must still
              // show the user's draft instead of the older entity state.
              slider.blur();
              await window.__epTelemetryBurst(8, 4);
              await new Promise((resolve) => setTimeout(resolve, 80));
              const stationary = {
                slider: slider.value,
                label: label?.textContent?.trim() || "",
              };

              slider.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
              await new Promise((resolve) => setTimeout(resolve, 120));
              const entityId = window.__epPanel._entityId("emhass_minimum_soc");
              const currentSlider = root.querySelector('input[data-ep-v038-soc="min"]');
              return {
                stationary,
                actual: window.__epHass.states[entityId]?.state,
                draft: currentSlider?.dataset.epSocDraft || "",
              };
            }
            """
        )
        result["present"] = True
        result["slider_kept_draft"] = measured["stationary"]["slider"] == "37"
        result["label_kept_draft"] = measured["stationary"]["label"] == "37%"
        result["acknowledged"] = (
            str(measured["actual"]) == "37" and measured["draft"] == ""
        )
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def control_style(page: Page, selector: str) -> dict[str, str]:
    return page.evaluate(
        """
        selector => {
          const node = window.__epPanel.shadowRoot.querySelector(selector);
          if (!node) return {};
          const style = getComputedStyle(node);
          return {
            backgroundColor: style.backgroundColor,
            backgroundImage: style.backgroundImage,
            borderColor: style.borderColor,
            boxShadow: style.boxShadow,
            color: style.color,
            transform: style.transform,
          };
        }
        """,
        selector,
    )


def wait_service_count(page: Page, entity_id: str, expected: int) -> None:
    page.wait_for_function(
        """
        ([entityId, expected]) => window.__epServiceCalls.filter(
          call => call.data?.entity_id === entityId
        ).length === expected
        """,
        arg=[entity_id, expected],
        timeout=10_000,
    )


def selection_snapshot(page: Page, selector: str, key: str) -> dict[str, object]:
    return page.evaluate(
        """
        ([selector, key]) => {
          const buttons = [...window.__epPanel.shadowRoot.querySelectorAll(selector)];
          const active = buttons.filter(button => button.classList.contains('active'));
          const pressed = buttons.filter(button => button.getAttribute('aria-pressed') === 'true');
          return {
            count: buttons.length,
            active: active.length,
            pressed: pressed.length,
            activeKey: active[0]?.dataset?.[key] || null,
            pressedKey: pressed[0]?.dataset?.[key] || null,
          };
        }
        """,
        [selector, key],
    )


def exercise_touch_controls(page: Page, profile: Profile) -> dict[str, object]:
    """Exercise repeated real taps and verify semantic, visual and action state."""
    enabled = profile.touch and EXPECTED_ENTRYPOINT in {"v043", "v044", "v045"}
    result: dict[str, object] = {
        "ran": enabled,
        "touch_media": False,
        "optimize": False,
        "emhass": False,
        "battery": False,
        "quick_actions": False,
        "menu_cycles": False,
        "hover_reset": False,
        "render_during_press": False,
        "post_structure": False,
        "telemetry_complete": False,
        "calls": {},
        "stage": "disabled",
        "error": None,
    }
    if not enabled:
        return result

    try:
        result["stage"] = "ready"
        page.wait_for_function(
            """
            () => Boolean(
              !window.__epPanel.shadowRoot.querySelector('.ep-optimize-now')?.disabled &&
              !window.__epPanel.shadowRoot.querySelector('[data-costfun="cost"]')?.disabled &&
              !window.__epPanel.shadowRoot.querySelector('[data-action="max_export"]')?.disabled &&
              !window.__epPanel.shadowRoot.querySelector('[data-ep-v038-profile="gold_rush"]')?.disabled
            )
            """,
            timeout=10_000,
        )
        page.evaluate(
            """
            () => {
              window.__epResetActionLogs();
              window.__epTouchTelemetry = window.__epTelemetryBurst(120, 5);
            }
            """
        )
        result["touch_media"] = page.evaluate(
            "matchMedia('(hover: none)').matches || matchMedia('(pointer: coarse)').matches"
        )

        initial_styles = {
            "optimize": control_style(page, ".ep-optimize-now"),
            "emhass": control_style(page, '[data-costfun="cost"]'),
            "battery": control_style(page, '[data-ep-v038-profile="gold_rush"]'),
            "quick": control_style(page, '[data-action="max_export"]'),
        }

        optimize_id = page.evaluate("window.__epPanel._entityId('optimize_now')")
        result["stage"] = "optimize"
        revision_before = page.evaluate(
            "window.__epHass.states[window.__epPanel._entityId('optimize_now')].attributes.plan_revision"
        )
        for index in range(3):
            if index == 2:
                page.evaluate("window.__epRenderOnNextPointerDown()")
            activate(page, profile, ".ep-optimize-now")
            wait_service_count(page, optimize_id, index + 1)
            page.wait_for_function(
                "() => !window.__epPanel.shadowRoot.querySelector('.ep-optimize-now')?.disabled",
                timeout=10_000,
            )
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPointerDownMain &&
              window.__epPointerDownMain !== window.__epPanel.shadowRoot.querySelector('main')
            )
            """,
            timeout=10_000,
        )
        revision_after = page.evaluate(
            "window.__epHass.states[window.__epPanel._entityId('optimize_now')].attributes.plan_revision"
        )
        optimize_calls = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.domain === 'button' && call.service === 'press' &&
                call.data?.entity_id === entityId
            ).length
            """,
            optimize_id,
        )
        result["optimize"] = optimize_calls == 3 and revision_after >= revision_before + 3
        result["render_during_press"] = optimize_calls == 3
        page.wait_for_timeout(80)
        hover_states = {
            "optimize": control_style(page, ".ep-optimize-now") == initial_styles["optimize"]
        }

        costfun_id = page.evaluate(
            "window.__epPanel._entityId('emhass_cost_function')"
        )
        result["stage"] = "emhass"
        costfun_expected = [
            ("cost", "Cost"),
            ("self-consumption", "Self-consumption"),
            ("profit", "Profit"),
            ("cost", "Cost"),
        ]
        emhass_snapshots: list[dict[str, object]] = []
        for index, (raw, _option) in enumerate(costfun_expected):
            activate(page, profile, f'[data-costfun="{raw}"]')
            wait_service_count(page, costfun_id, index + 1)
            page.wait_for_function(
                """
                raw => {
                  const root = window.__epPanel.shadowRoot;
                  const active = root.querySelectorAll('.ep-v016-costfun-button.active');
                  const pressed = root.querySelectorAll('.ep-v016-costfun-button[aria-pressed="true"]');
                  return active.length === 1 && pressed.length === 1 &&
                    active[0].dataset.costfun === raw && pressed[0].dataset.costfun === raw;
                }
                """,
                arg=raw,
                timeout=10_000,
            )
            emhass_snapshots.append(
                selection_snapshot(page, ".ep-v016-costfun-button", "costfun")
            )
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const entityId = panel._entityId('emhass_cost_function');
              window.__epSetEntity(entityId, 'Profit', { emhass_costfun: 'profit' });
              panel._queueRender();
            }
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-costfun="profit"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )
        page.wait_for_timeout(80)
        hover_states["emhass"] = (
            control_style(page, '[data-costfun="cost"]') == initial_styles["emhass"]
        )
        emhass_options = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.domain === 'select' && call.service === 'select_option' &&
                call.data?.entity_id === entityId
            ).map(call => call.data.option)
            """,
            costfun_id,
        )
        result["emhass"] = (
            emhass_options == [option for _raw, option in costfun_expected]
            and all(
                snapshot["active"] == 1
                and snapshot["pressed"] == 1
                and snapshot["activeKey"] == raw
                and snapshot["pressedKey"] == raw
                for snapshot, (raw, _option) in zip(
                    emhass_snapshots, costfun_expected, strict=True
                )
            )
        )

        battery_modes = ["gold_rush", "mad_steve", "balanced", "gold_rush"]
        result["stage"] = "battery"
        battery_snapshots: list[dict[str, object]] = []
        for index, mode in enumerate(battery_modes):
            activate(page, profile, f'[data-ep-v038-profile="{mode}"]')
            page.wait_for_function(
                """
                expected => window.__epWsCalls.filter(
                  call => call.type === 'gw_energypilot/battery_saver/set'
                ).length === expected
                """,
                arg=index + 1,
                timeout=10_000,
            )
            page.wait_for_function(
                """
                mode => {
                  const root = window.__epPanel.shadowRoot;
                  const pressed = root.querySelectorAll(
                    '.ep-v038-profile[aria-pressed="true"]'
                  );
                  return pressed.length === 1 &&
                    pressed[0].dataset.epV038Profile === mode &&
                    root.querySelectorAll('.ep-v038-badge').length === 1;
                }
                """,
                arg=mode,
                timeout=10_000,
            )
            page.wait_for_function(
                """
                () => Boolean(
                  !window.__epPanel.__epV038BatterySaver?.busy &&
                  !window.__epPanel.__epV038BatterySaver?.loading &&
                  !window.__epPanel.shadowRoot.querySelector(
                    '.ep-v038-profile'
                  )?.disabled
                )
                """,
                timeout=10_000,
            )
            battery_snapshots.append(
                page.evaluate(
                    """
                    () => {
                      const root = window.__epPanel.shadowRoot;
                      const pressed = [...root.querySelectorAll(
                        '.ep-v038-profile[aria-pressed="true"]'
                      )];
                      return {
                        pressed: pressed.length,
                        key: pressed[0]?.dataset.epV038Profile || null,
                        badges: root.querySelectorAll('.ep-v038-badge').length,
                      };
                    }
                    """
                )
            )
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const cache = panel.__epV038BatterySaver;
              cache.data = { ...cache.data, managed: true, mode: 'balanced' };
              cache.pendingMode = null;
              cache.busy = false;
              cache.loading = false;
              panel.__epV041RefreshStrategy();
            }
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-ep-v038-profile="balanced"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )
        page.wait_for_timeout(80)
        hover_states["battery"] = (
            control_style(page, '[data-ep-v038-profile="gold_rush"]')
            == initial_styles["battery"]
        )
        battery_call_modes = page.evaluate(
            """
            () => window.__epWsCalls.filter(
              call => call.type === 'gw_energypilot/battery_saver/set'
            ).map(call => call.mode)
            """
        )
        result["battery"] = (
            battery_call_modes == battery_modes
            and all(
                snapshot["pressed"] == 1
                and snapshot["key"] == mode
                and snapshot["badges"] == 1
                for snapshot, mode in zip(
                    battery_snapshots, battery_modes, strict=True
                )
            )
        )

        quick_keys = [
            "max_export",
            "battery_pause",
            "max_charge",
            "resume_auto",
            "max_export",
        ]
        result["stage"] = "quick-actions"
        quick_snapshots: list[dict[str, object]] = []
        quick_ids = {
            key: page.evaluate(f"window.__epPanel._entityId('{key}')")
            for key in set(quick_keys)
        }
        quick_before = page.evaluate(
            """
            ids => window.__epServiceCalls.filter(
              call => ids.includes(call.data?.entity_id)
            ).length
            """,
            list(quick_ids.values()),
        )
        for index, key in enumerate(quick_keys):
            activate(page, profile, f'[data-action="{key}"]')
            page.wait_for_function(
                """
                ([ids, expected]) => window.__epServiceCalls.filter(
                  call => ids.includes(call.data?.entity_id)
                ).length === expected
                """,
                arg=[list(quick_ids.values()), quick_before + index + 1],
                timeout=10_000,
            )
            page.wait_for_function(
                """
                key => {
                  const root = window.__epPanel.shadowRoot;
                  const active = root.querySelectorAll('.ep-battery-action.active');
                  return active.length === 1 && active[0].dataset.action === key;
                }
                """,
                arg=key,
                timeout=10_000,
            )
            quick_snapshots.append(
                page.evaluate(
                    """
                    () => {
                      const active = [...window.__epPanel.shadowRoot.querySelectorAll(
                        '.ep-battery-action.active'
                      )];
                      return {
                        active: active.length,
                        key: active[0]?.dataset.action || null,
                      };
                    }
                    """
                )
            )
        page.evaluate(
            """
            () => {
              window.__epSetEntityByKey('control_command', 'manual_battery_hold');
              window.__epSetEntityByKey('automatic_control', 'off');
              window.__epPanel._queueRender();
            }
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-action="battery_pause"]'
            )?.classList.contains('active')
            """,
            timeout=10_000,
        )
        page.wait_for_timeout(80)
        hover_states["quick"] = (
            control_style(page, '[data-action="max_export"]')
            == initial_styles["quick"]
        )
        quick_call_keys = page.evaluate(
            """
            ids => window.__epServiceCalls.filter(
              call => Object.values(ids).includes(call.data?.entity_id)
            ).map(call => Object.entries(ids).find(([, entityId]) =>
              entityId === call.data.entity_id
            )?.[0] || null)
            """,
            quick_ids,
        )
        result["quick_actions"] = (
            quick_call_keys == quick_keys
            and all(
                snapshot["active"] == 1 and snapshot["key"] == key
                for snapshot, key in zip(quick_snapshots, quick_keys, strict=True)
            )
        )

        menu_ok = True
        result["stage"] = "menu"
        for _index in range(3):
            activate(page, profile, ".ep-layout-button")
            page.wait_for_function(
                "() => window.__epPanel.shadowRoot.querySelectorAll('.ep-layout-menu').length === 1",
                timeout=10_000,
            )
            activate(page, profile, ".ep-menu-close")
            page.wait_for_function(
                "() => window.__epPanel.shadowRoot.querySelectorAll('.ep-layout-menu').length === 0",
                timeout=10_000,
            )
            menu_ok = menu_ok and page.evaluate(
                "window.__epPanel.shadowRoot.querySelectorAll('.ep-layout-menu').length === 0"
            )
        result["menu_cycles"] = menu_ok

        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              window.__epTouchStructureMain = panel.shadowRoot.querySelector('main');
              panel.narrow = !panel.narrow;
            }
            """
        )
        result["stage"] = "post-structure"
        page.wait_for_function(
            """
            () => Boolean(
              window.__epTouchStructureMain !==
                window.__epPanel.shadowRoot.querySelector('main') &&
              !window.__epPanel.shadowRoot.querySelector('.ep-optimize-now')?.disabled &&
              !window.__epPanel.shadowRoot.querySelector('[data-costfun="self-consumption"]')?.disabled &&
              !window.__epPanel.shadowRoot.querySelector('[data-ep-v038-profile="mad_steve"]')?.disabled &&
              !window.__epPanel.shadowRoot.querySelector('[data-action="resume_auto"]')?.disabled
            )
            """,
            timeout=10_000,
        )
        page.wait_for_timeout(120)
        post_before = {
            "optimize": page.evaluate(
                """
                entityId => window.__epServiceCalls.filter(
                  call => call.data?.entity_id === entityId
                ).length
                """,
                optimize_id,
            ),
            "emhass": page.evaluate(
                """
                entityId => window.__epServiceCalls.filter(
                  call => call.data?.entity_id === entityId
                ).length
                """,
                costfun_id,
            ),
            "battery": page.evaluate(
                """
                () => window.__epWsCalls.filter(
                  call => call.type === 'gw_energypilot/battery_saver/set'
                ).length
                """
            ),
            "quick": page.evaluate(
                """
                ids => window.__epServiceCalls.filter(
                  call => ids.includes(call.data?.entity_id)
                ).length
                """,
                list(quick_ids.values()),
            ),
        }
        activate(page, profile, ".ep-optimize-now")
        wait_service_count(page, optimize_id, post_before["optimize"] + 1)
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-optimize-now')?.disabled",
            timeout=10_000,
        )
        activate(page, profile, '[data-costfun="self-consumption"]')
        wait_service_count(page, costfun_id, post_before["emhass"] + 1)
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.shadowRoot.querySelector(
                '[data-costfun="self-consumption"]'
              )?.getAttribute('aria-pressed') === 'true' &&
              !window.__epPanel.shadowRoot.querySelector(
                '[data-costfun="self-consumption"]'
              )?.disabled
            )
            """,
            timeout=10_000,
        )
        activate(page, profile, '[data-ep-v038-profile="mad_steve"]')
        page.wait_for_function(
            """
            expected => window.__epWsCalls.filter(
              call => call.type === 'gw_energypilot/battery_saver/set'
            ).length === expected
            """,
            arg=post_before["battery"] + 1,
            timeout=10_000,
        )
        page.wait_for_function(
            """
            () => Boolean(
              !window.__epPanel.__epV038BatterySaver?.busy &&
              !window.__epPanel.__epV038BatterySaver?.loading &&
              !window.__epPanel.shadowRoot.querySelector(
                '[data-ep-v038-profile="mad_steve"]'
              )?.disabled
            )
            """,
            timeout=10_000,
        )
        activate(page, profile, '[data-action="resume_auto"]')
        page.wait_for_function(
            """
            ([ids, expected]) => window.__epServiceCalls.filter(
              call => ids.includes(call.data?.entity_id)
            ).length === expected
            """,
            arg=[list(quick_ids.values()), post_before["quick"] + 1],
            timeout=10_000,
        )
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.shadowRoot.querySelector(
                '[data-action="resume_auto"]'
              )?.classList.contains('active')
            )
            """,
            timeout=10_000,
        )
        activate(page, profile, ".ep-layout-button")
        page.wait_for_function(
            "() => Boolean(window.__epPanel.shadowRoot.querySelector('.ep-layout-menu'))",
            timeout=10_000,
        )
        activate(page, profile, ".ep-menu-close")
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-layout-menu')",
            timeout=10_000,
        )
        result["post_structure"] = True

        page.evaluate("async () => await window.__epTouchTelemetry")
        page.wait_for_timeout(180)
        page.wait_for_function(
            """
            () => Boolean(
              !window.__epPanel.__epV038BatterySaver?.busy &&
              !window.__epPanel.__epV038BatterySaver?.loading &&
              !window.__epPanel.__epV027BatteryPlanPromise &&
              !window.__epPanel.shadowRoot.querySelector('.ep-optimize-now')?.disabled
            )
            """,
            timeout=15_000,
        )
        result["telemetry_complete"] = True
        result["hover_reset"] = all(hover_states.values())
        result["calls"] = {
            "optimize": optimize_calls,
            "emhass": emhass_options,
            "battery": battery_call_modes,
            "quick": quick_call_keys,
            "hover": hover_states,
        }
        result["stage"] = "complete"
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_optimize_stability(page: Page, profile: Profile) -> dict[str, object]:
    """Prove that the inherited v0.44 Optimize action keeps the interaction DOM."""
    enabled = EXPECTED_ENTRYPOINT in {"v044", "v045"}
    result: dict[str, object] = {
        "ran": enabled,
        "single_call": False,
        "no_full_render": False,
        "main_stable": False,
        "optimize_stable": False,
        "layout_stable": False,
        "automatic_stable": False,
        "strategy_stable": False,
        "bottom_anchor_stable": False,
        "button_position_stable": False,
        "scroll_working": False,
        "button_idle": False,
        "marker": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        button = shadow(page, ".ep-optimize-now")
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
              const optimize = root.querySelector('.ep-optimize-now');
              const rect = optimize?.getBoundingClientRect();
              const maximum = scroller.scrollHeight - scroller.clientHeight;
              window.__epOptimizeIdentity = {
                main: root.querySelector('main'),
                optimize,
                layout: root.querySelector('.ep-layout-button'),
                automatic: root.querySelector('#auto-toggle'),
                strategy: root.querySelector('[data-ep-v038-profile="mad_steve"]'),
              };
              window.__epOptimizeRenderCount = 0;
              const originalRender = panel._render;
              panel._render = function v044OptimizeRenderProbe(...args) {
                window.__epOptimizeRenderCount += 1;
                return originalRender.apply(this, args);
              };
              return {
                revision: Number(
                  window.__epHass.states[optimizeId]?.attributes?.plan_revision || 0
                ),
                calls: window.__epServiceCalls.filter(
                  call => call.domain === 'button' && call.service === 'press' &&
                    call.data?.entity_id === optimizeId
                ).length,
                maximum,
                scrollTop: scroller.scrollTop,
                bottomDistance: maximum - scroller.scrollTop,
                buttonTop: rect?.top ?? null,
              };
            }
            """
        )

        activate(page, profile, ".ep-optimize-now")
        page.wait_for_function(
            """
            previousRevision => {
              const panel = window.__epPanel;
              const optimizeId = panel._entityId('optimize_now');
              const revision = Number(
                window.__epHass.states[optimizeId]?.attributes?.plan_revision || 0
              );
              const chartRevision = Number(
                panel.__epV027BatteryPlanData?.payload?.plan_revision || 0
              );
              const button = panel.shadowRoot.querySelector('.ep-optimize-now');
              return Boolean(
                revision === previousRevision + 1 &&
                chartRevision === revision &&
                !panel.__epV027BatteryPlanPromise &&
                button?.getAttribute('aria-busy') === 'false' &&
                !button.disabled
              );
            }
            """,
            arg=initial["revision"],
            timeout=15_000,
        )
        page.wait_for_timeout(350)
        measured = page.evaluate(
            """
            async initial => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const scroller = window.__epScroller;
              const optimizeId = panel._entityId('optimize_now');
              const optimize = root.querySelector('.ep-optimize-now');
              const rect = optimize?.getBoundingClientRect();
              const maximum = scroller.scrollHeight - scroller.clientHeight;
              const afterOptimize = scroller.scrollTop;
              const downSpace = maximum - afterOptimize;
              const distance = Math.max(320, Math.round(scroller.clientHeight * 0.45));
              const target = downSpace >= 250
                ? Math.min(maximum, afterOptimize + distance)
                : Math.max(0, afterOptimize - Math.min(distance, afterOptimize));
              const calls = window.__epServiceCalls.filter(
                call => call.domain === 'button' && call.service === 'press' &&
                  call.data?.entity_id === optimizeId
              ).length;
              const beforeProbe = {
                calls,
                renderCount: window.__epOptimizeRenderCount,
                mainStable: window.__epOptimizeIdentity.main === root.querySelector('main'),
                optimizeStable: window.__epOptimizeIdentity.optimize === optimize,
                layoutStable:
                  window.__epOptimizeIdentity.layout === root.querySelector('.ep-layout-button'),
                automaticStable:
                  window.__epOptimizeIdentity.automatic === root.querySelector('#auto-toggle'),
                strategyStable:
                  window.__epOptimizeIdentity.strategy === root.querySelector(
                    '[data-ep-v038-profile="mad_steve"]'
                  ),
                bottomAnchorDelta:
                  (maximum - afterOptimize) - initial.bottomDistance,
                scrollTopDelta: afterOptimize - initial.scrollTop,
                scrollRangeDelta: maximum - initial.maximum,
                buttonTopDelta:
                  rect && initial.buttonTop !== null ? rect.top - initial.buttonTop : null,
                probeDistance: Math.abs(target - afterOptimize),
                target,
                buttonBusy: optimize?.getAttribute('aria-busy'),
                buttonDisabled: Boolean(optimize?.disabled),
                marker: optimize?.dataset?.epV044StableOptimize || '',
              };
              scroller.scrollTop = target;
              await new Promise((resolve) => setTimeout(resolve, 180));
              return { ...beforeProbe, scrollAfterProbe: scroller.scrollTop };
            }
            """,
            initial,
        )
        result.update(
            {
                "single_call": measured["calls"] == initial["calls"] + 1,
                "no_full_render": measured["renderCount"] == 0,
                "main_stable": measured["mainStable"],
                "optimize_stable": measured["optimizeStable"],
                "layout_stable": measured["layoutStable"],
                "automatic_stable": measured["automaticStable"],
                "strategy_stable": measured["strategyStable"],
                "bottom_anchor_stable": abs(measured["bottomAnchorDelta"]) <= 5,
                "button_position_stable": (
                    measured["buttonTopDelta"] is not None
                    and abs(measured["buttonTopDelta"]) <= 5
                    and abs(
                        measured["scrollTopDelta"] - measured["scrollRangeDelta"]
                    )
                    <= 5
                ),
                "scroll_working": (
                    measured["probeDistance"] >= 200
                    and abs(measured["scrollAfterProbe"] - measured["target"]) <= 5
                ),
                "button_idle": (
                    measured["buttonBusy"] == "false"
                    and measured["buttonDisabled"] is False
                ),
                "marker": measured["marker"] == "1",
            }
        )
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_plan_refresh(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "ready": False,
        "data_changed": False,
        "card_changed": False,
        "main_stable": False,
        "layout_control_stable": False,
        "auto_control_stable": False,
        "optimize_control_stable": False,
        "costfun_control_stable": False,
        "max_export_control_stable": False,
        "strategy_control_stable": False,
        "error": None,
    }
    try:
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.__epV027BatteryPlanData?.payload &&
              !window.__epPanel.__epV027BatteryPlanPromise &&
              window.__epPanel.shadowRoot.querySelector('.ep-v027-battery-plan-card')
            )
            """,
            timeout=15_000,
        )
        result["ready"] = True
        before = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              window.__epPlanIdentity = {
                main: root.querySelector('main'),
                layout: root.querySelector('.ep-layout-button'),
                auto: root.querySelector('#auto-toggle'),
                optimize: root.querySelector('.ep-optimize-now'),
                costfun: root.querySelector('[data-costfun="profit"]'),
                maxExport: root.querySelector('[data-action="max_export"]'),
                strategy: root.querySelector('[data-ep-v038-profile="mad_steve"]'),
                card: root.querySelector('.ep-v027-battery-plan-card'),
              };
              return {
                revision: window.__epPanel.__epV027BatteryPlanData?.payload?.plan_revision,
                renderKey: window.__epPlanIdentity.card?.dataset.epRenderKey || '',
              };
            }
            """
        )
        revision = page.evaluate("window.__epAdvancePlan()")
        page.wait_for_function(
            """
            revision => Boolean(
              window.__epPanel.__epV027BatteryPlanData?.payload?.plan_revision === revision &&
              !window.__epPanel.__epV027BatteryPlanPromise
            )
            """,
            arg=revision,
            timeout=15_000,
        )
        page.wait_for_function(
            """
            previousKey => {
              const card = window.__epPanel.shadowRoot.querySelector('.ep-v027-battery-plan-card');
              return Boolean(card && card.dataset.epRenderKey !== previousKey);
            }
            """,
            arg=before["renderKey"],
            timeout=10_000,
        )
        result.update(
            page.evaluate(
                """
                previousRevision => {
                  const root = window.__epPanel.shadowRoot;
                  return {
                    data_changed:
                      window.__epPanel.__epV027BatteryPlanData?.payload?.plan_revision !== previousRevision,
                    card_changed:
                      window.__epPlanIdentity.card !== root.querySelector('.ep-v027-battery-plan-card'),
                    main_stable: window.__epPlanIdentity.main === root.querySelector('main'),
                    layout_control_stable:
                      window.__epPlanIdentity.layout === root.querySelector('.ep-layout-button'),
                    auto_control_stable:
                      window.__epPlanIdentity.auto === root.querySelector('#auto-toggle'),
                    optimize_control_stable:
                      window.__epPlanIdentity.optimize === root.querySelector('.ep-optimize-now'),
                    costfun_control_stable:
                      window.__epPlanIdentity.costfun === root.querySelector('[data-costfun="profit"]'),
                    max_export_control_stable:
                      window.__epPlanIdentity.maxExport === root.querySelector('[data-action="max_export"]'),
                    strategy_control_stable:
                      window.__epPlanIdentity.strategy === root.querySelector(
                        '[data-ep-v038-profile="mad_steve"]'
                      ),
                  };
                }
                """,
                before["revision"],
            )
        )
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_language(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "localized": False,
        "main_stable_during_telemetry": False,
        "idle_delta": None,
        "error": None,
    }
    try:
        page.evaluate("window.__epSetLanguage('nl')")
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.panel-card.controller .section-title-row h2'
            )?.textContent.trim() === 'Regelaar'
            """,
            timeout=10_000,
        )
        result["localized"] = True
        telemetry = page.evaluate(
            """
            async () => {
              const root = window.__epPanel.shadowRoot;
              const scroller = window.__epScroller;
              window.__epDutchMain = root.querySelector('main');
              const max = scroller.scrollHeight - scroller.clientHeight;
              scroller.scrollTop = Math.max(0, Math.round(max * 0.42));
              await new Promise((resolve) => setTimeout(resolve, 100));
              const before = scroller.scrollTop;
              await window.__epTelemetryBurst(35, 4);
              await new Promise((resolve) => setTimeout(resolve, 850));
              return {
                before,
                after: scroller.scrollTop,
                mainStable:
                  window.__epDutchMain === window.__epPanel.shadowRoot.querySelector('main'),
              };
            }
            """
        )
        result["main_stable_during_telemetry"] = telemetry["mainStable"]
        result["idle_delta"] = telemetry["after"] - telemetry["before"]
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_structural_rerender(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
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
        menu = open_and_close_menu(page)
        result["menu_open"] = menu["open"]
        result["menu_close"] = menu["close"]
        result["error"] = menu["error"]
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_pv_insight(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "ran": False,
        "topology_rendered": False,
        "source_count": 0,
        "total_matches": False,
        "flow_matches": False,
        "telemetry_main_stable": False,
        "external_value_matches": False,
        "scroll_delta": None,
        "error": None,
    }
    try:
        page.evaluate(
            """
            () => {
              window.__epPvBeforeTopologyMain =
                window.__epPanel.shadowRoot.querySelector('main');
              window.__epSetExternalPv(1200);
            }
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot
              .querySelectorAll('.energy-card.solar [data-pv-source-index]').length === 2
            """,
            timeout=10_000,
        )
        page.wait_for_timeout(180)
        topology = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const aggregate = window.__epHass.states[
                panel._entityId('pv_generation_power')
              ];
              const expected = panel._formatPower(Number(aggregate.state));
              const main = root.querySelector('main');
              window.__epPvTelemetryMain = main;
              const scroller = window.__epScroller;
              scroller.scrollTop = Math.max(
                0,
                Math.round((scroller.scrollHeight - scroller.clientHeight) * 0.36)
              );
              window.__epPvScrollBefore = scroller.scrollTop;
              return {
                topologyRendered: window.__epPvBeforeTopologyMain !== main,
                sourceCount: root.querySelectorAll(
                  '.energy-card.solar [data-pv-source-index]'
                ).length,
                totalMatches:
                  root.querySelector('.energy-card.solar .hero-value')?.textContent === expected,
                flowMatches:
                  root.querySelector('.ep-flow-solar .ep-flow-node-value')?.textContent === expected,
              };
            }
            """
        )
        page.evaluate("window.__epSetExternalPv(1700)")
        page.wait_for_timeout(260)
        telemetry = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const external = root.querySelector(
                '.energy-card.solar [data-pv-source-index="1"] .metric-value'
              );
              return {
                mainStable: window.__epPvTelemetryMain === root.querySelector('main'),
                externalMatches: external?.textContent === panel._formatPower(1700),
                scrollDelta: window.__epScroller.scrollTop - window.__epPvScrollBefore,
              };
            }
            """
        )
        result.update(
            {
                "ran": True,
                "topology_rendered": topology["topologyRendered"],
                "source_count": topology["sourceCount"],
                "total_matches": topology["totalMatches"],
                "flow_matches": topology["flowMatches"],
                "telemetry_main_stable": telemetry["mainStable"],
                "external_value_matches": telemetry["externalMatches"],
                "scroll_delta": telemetry["scrollDelta"],
            }
        )
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_pv_settings(page: Page, profile: Profile) -> dict[str, object]:
    result: dict[str, object] = {
        "ran": False,
        "tab_present": False,
        "internal_checked": False,
        "external_fields": 0,
        "entity_search_contains_source": False,
        "closed": False,
        "error": None,
    }
    try:
        activate(page, profile, ".ep-v016-settings-button")
        page.wait_for_selector(
            "gw-energypilot-panel >> [data-settings-tab=\"pv\"]",
            timeout=10_000,
        )
        result["tab_present"] = True
        activate(page, profile, '[data-settings-tab="pv"]')
        page.wait_for_selector(
            "gw-energypilot-panel >> .ep-v016-form[data-section=\"pv\"]",
            timeout=10_000,
        )
        state = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const form = root.querySelector('.ep-v016-form[data-section="pv"]');
              return {
                internalChecked: Boolean(
                  form?.querySelector('[data-setting-key="enable_internal_pv"]')?.checked
                ),
                externalFields: form?.querySelectorAll(
                  '[data-setting-key^="external_pv_entity_"]'
                ).length || 0,
                entitySearchContainsSource: [...(form?.querySelectorAll('datalist option') || [])]
                  .some((option) => option.value === 'sensor.external_roof_pv'),
              };
            }
            """
        )
        result["internal_checked"] = state["internalChecked"]
        result["external_fields"] = state["externalFields"]
        result["entity_search_contains_source"] = state["entitySearchContainsSource"]
        activate(page, profile, ".ep-v016-back")
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-v016-settings')",
            timeout=10_000,
        )
        result["closed"] = True
        result["ran"] = True
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_profile(page: Page, profile: Profile) -> dict[str, object]:
    page.goto(HARNESS, wait_until="domcontentloaded", timeout=30_000)
    page.evaluate("window.__epReady")
    page.wait_for_function(
        """
        () => Boolean(
          window.__epPanel?.shadowRoot?.querySelector('.ep-layout-button') &&
          window.__epPanel.shadowRoot.querySelector('#auto-toggle') &&
          window.__epPanel.shadowRoot.querySelectorAll('[data-ep-card]').length >= 8
        )
        """,
        timeout=10_000,
    )
    page.wait_for_timeout(350)

    initial = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          const scroller = window.__epScroller;
          window.__epTelemetryIdentity = {
            main: root.querySelector('main'),
            layout: root.querySelector('.ep-layout-button'),
            auto: root.querySelector('#auto-toggle'),
            optimize: root.querySelector('.ep-optimize-now'),
            costfun: root.querySelector('[data-costfun="profit"]'),
            maxExport: root.querySelector('[data-action="max_export"]'),
            strategy: root.querySelector('[data-ep-v038-profile="mad_steve"]'),
          };
          const max = scroller.scrollHeight - scroller.clientHeight;
          scroller.scrollTop = Math.max(0, Math.round(max * 0.55));
          return {
            entrypoint: window.__epEntryPoint,
            stableMarker: root.querySelector('main')?.dataset.epV041StableDom || '',
            scrollTop: scroller.scrollTop,
            scrollHeight: scroller.scrollHeight,
            clientHeight: scroller.clientHeight,
            max,
            cards: root.querySelectorAll('[data-ep-card]').length,
            buttons: root.querySelectorAll('button').length,
          };
        }
        """
    )
    page.wait_for_timeout(100)

    idle_before = page.evaluate("window.__epScroller.scrollTop")
    page.evaluate("window.__epTelemetryBurst(40, 4)")
    page.wait_for_timeout(900)
    idle_after = page.evaluate("window.__epScroller.scrollTop")
    telemetry_identity = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          return {
            main: window.__epTelemetryIdentity.main === root.querySelector('main'),
            layout: window.__epTelemetryIdentity.layout === root.querySelector('.ep-layout-button'),
            auto: window.__epTelemetryIdentity.auto === root.querySelector('#auto-toggle'),
            optimize:
              window.__epTelemetryIdentity.optimize === root.querySelector('.ep-optimize-now'),
            costfun:
              window.__epTelemetryIdentity.costfun === root.querySelector('[data-costfun="profit"]'),
            max_export:
              window.__epTelemetryIdentity.maxExport === root.querySelector('[data-action="max_export"]'),
            strategy: window.__epTelemetryIdentity.strategy === root.querySelector(
              '[data-ep-v038-profile="mad_steve"]'
            ),
          };
        }
        """
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
          const telemetry = window.__epTelemetryBurst(75, 4);
          const steps = 55;
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

    pv_insight = exercise_pv_insight(page)
    pv_settings = exercise_pv_settings(page, profile)
    touch_controls = exercise_touch_controls(page, profile)
    optimize_stability = exercise_optimize_stability(page, profile)
    menu = open_and_close_menu(page)
    automatic = exercise_automatic_control(page)
    soc_slider = exercise_soc_slider_draft(page)
    strategy = exercise_strategy(page)
    plan = exercise_plan_refresh(page)
    language_result = exercise_language(page)
    structural = exercise_structural_rerender(page)

    return {
        "profile": profile.name,
        "initial": initial,
        "idle_before": idle_before,
        "idle_after": idle_after,
        "idle_delta": idle_after - idle_before,
        "telemetry_identity": telemetry_identity,
        "motion": motion,
        "pv_insight": pv_insight,
        "pv_settings": pv_settings,
        "touch_controls": touch_controls,
        "optimize_stability": optimize_stability,
        "menu": menu,
        "automatic": automatic,
        "soc_slider": soc_slider,
        "strategy": strategy,
        "plan": plan,
        "language": language_result,
        "structural": structural,
        "animation": animation_summary(page),
        "errors": page.evaluate("window.__epErrors"),
        "unknown_ws": page.evaluate("Array.from(window.__epUnknownWsTypes).sort()"),
    }


def result_failures(profile: Profile, result: dict[str, object], page_errors: list[str]) -> list[str]:
    failures: list[str] = []
    name = profile.name
    initial = result["initial"]
    identity = result["telemetry_identity"]
    motion = result["motion"]
    pv_insight = result["pv_insight"]
    pv_settings = result["pv_settings"]
    touch_controls = result["touch_controls"]
    optimize_stability = result["optimize_stability"]
    menu = result["menu"]
    automatic = result["automatic"]
    soc_slider = result["soc_slider"]
    strategy = result["strategy"]
    plan = result["plan"]
    language_result = result["language"]
    structural = result["structural"]
    animation = result["animation"]

    if EXPECTED_ENTRYPOINT and initial["entrypoint"] != EXPECTED_ENTRYPOINT:
        failures.append(f"{name}: loaded {initial['entrypoint']} instead of {EXPECTED_ENTRYPOINT}")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS and initial["stableMarker"] != "1":
        failures.append(f"{name}: stable-DOM marker is missing")
    if initial["max"] < 500:
        failures.append(f"{name}: harness is not sufficiently scrollable")
    if initial["cards"] < 8 or initial["buttons"] < 20:
        failures.append(f"{name}: dashboard controls/cards did not initialize completely")
    if abs(result["idle_delta"]) > 2:
        failures.append(f"{name}: idle telemetry moved scroll by {result['idle_delta']} px")
    for key, stable in identity.items():
        if stable is not True:
            failures.append(f"{name}: telemetry replaced the {key} DOM node")
    if motion["backwards"] != 0:
        failures.append(f"{name}: scroll moved backwards during telemetry")
    if abs(motion["final"] - motion["target"]) > 5:
        failures.append(f"{name}: scrolling did not reach its target during telemetry")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS:
        if not all(
            pv_insight[key] is True
            for key in (
                "ran", "topology_rendered", "total_matches", "flow_matches",
                "telemetry_main_stable", "external_value_matches",
            )
        ) or pv_insight["source_count"] != 2:
            failures.append(f"{name}: combined PV topology/live patch regression failed")
        if abs(pv_insight["scroll_delta"] or 0) > 2:
            failures.append(f"{name}: PV telemetry moved scroll position")
        if pv_insight["error"]:
            failures.append(f"{name}: PV insight interaction error")
        if not all(
            pv_settings[key] is True
            for key in (
                "ran", "tab_present", "internal_checked",
                "entity_search_contains_source", "closed",
            )
        ) or pv_settings["external_fields"] != 4:
            failures.append(f"{name}: PV settings tab/entity-search regression failed")
        if pv_settings["error"]:
            failures.append(f"{name}: PV settings interaction error")
    if profile.touch and EXPECTED_ENTRYPOINT in {"v043", "v044", "v045"}:
        required_touch = (
            "ran", "touch_media", "optimize", "emhass", "battery",
            "quick_actions", "menu_cycles", "hover_reset",
            "render_during_press", "post_structure", "telemetry_complete",
        )
        if not all(touch_controls[key] is True for key in required_touch):
            failures.append(f"{name}: repeated touch-control regression failed")
        if touch_controls["error"]:
            failures.append(f"{name}: touch-control interaction error")
    if EXPECTED_ENTRYPOINT in {"v044", "v045"}:
        required_optimize = (
            "ran", "single_call", "no_full_render", "main_stable",
            "optimize_stable", "layout_stable", "automatic_stable",
            "strategy_stable", "bottom_anchor_stable", "button_position_stable",
            "scroll_working", "button_idle", "marker",
        )
        if not all(optimize_stability[key] is True for key in required_optimize):
            failures.append(f"{name}: Optimize now rebuilt or moved interaction DOM")
        if optimize_stability["error"]:
            failures.append(f"{name}: Optimize now stability interaction error")
    if menu["open"] is not True or menu["close"] is not True:
        failures.append(f"{name}: dashboard menu did not reliably open and close")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS and menu["motion_disabled"] is not True:
        failures.append(f"{name}: stable-DOM motion control is not locked off")
    if menu["error"]:
        failures.append(f"{name}: dashboard menu interaction error")
    if not all(
        automatic[key] is True
        for key in ("present", "off_changed", "on_changed", "main_stable")
    ):
        failures.append(f"{name}: Automatic Control did not toggle stably twice")
    if automatic["error"]:
        failures.append(f"{name}: Automatic Control interaction error")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS and not all(
        soc_slider[key] is True
        for key in (
            "present", "slider_kept_draft", "label_kept_draft", "acknowledged",
        )
    ):
        failures.append(f"{name}: SOC slider draft was replaced by stale telemetry")
    if soc_slider["error"]:
        failures.append(f"{name}: SOC slider interaction error")
    if strategy["present"] is not True or strategy["changed"] is not True:
        failures.append(f"{name}: Battery Strategy button did not apply")
    if strategy["error"]:
        failures.append(f"{name}: Battery Strategy interaction error")
    if not all(
        plan[key] is True
        for key in (
            "ready", "data_changed", "card_changed", "main_stable",
            "layout_control_stable", "auto_control_stable",
            "optimize_control_stable", "costfun_control_stable",
            "max_export_control_stable", "strategy_control_stable",
        )
    ):
        failures.append(f"{name}: plan refresh rebuilt more than the graph card or did not refresh")
    if plan["error"]:
        failures.append(f"{name}: battery-plan refresh interaction error")
    if language_result["localized"] is not True:
        failures.append(f"{name}: Dutch structural render did not localize")
    if language_result["main_stable_during_telemetry"] is not True:
        failures.append(f"{name}: Dutch telemetry replaced the main DOM")
    if abs(language_result["idle_delta"] or 0) > 2:
        failures.append(f"{name}: Dutch telemetry moved scroll position")
    if structural["cards"] < 8 or structural["main_rebuilt"] is not True:
        failures.append(f"{name}: deliberate narrow-layout structural render failed")
    if structural["menu_open"] is not True or structural["menu_close"] is not True:
        failures.append(f"{name}: controls failed after a structural layout render")
    if structural["error"]:
        failures.append(f"{name}: post-structure menu interaction error")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS and (
        animation["animations"] != 0 or animation["transitions"] != 0
    ):
        failures.append(
            f"{name}: stable-DOM frontend still has {animation['animations']} animations and "
            f"{animation['transitions']} transitions"
        )
    if result["errors"] or page_errors:
        failures.append(f"{name}: JavaScript errors were reported")
    if result["unknown_ws"]:
        failures.append(f"{name}: harness encountered unknown WebSocket calls")
    return failures


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
                failures.extend(result_failures(profile, result, page_errors))
            except Exception as err:  # noqa: BLE001 - capture a usable CI artifact
                page_errors.append(f"fatal: {err}")
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
    output = Path("frontend-browser-results.json")
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failures:
        print("Browser diagnostic failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
