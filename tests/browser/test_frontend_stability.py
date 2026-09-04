#!/usr/bin/env python3
"""Real-browser desktop, iPad and iPhone frontend stability regressions."""

from __future__ import annotations

import contextlib
import http.server
import json
import socket
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from playwright.sync_api import BrowserType, Error as PlaywrightError, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HARNESS = "/tests/browser/frontend_harness.html"
EXPECTED_ENTRYPOINT: str | None = None
STABLE_ENTRYPOINTS = {"v041", "v042", "v043", "v044", "v045", "v046", "v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}


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
    page.evaluate(
        """
        selector => {
          const root = window.__epPanel.shadowRoot;
          const node = root.querySelector(selector);
          const disclosure = node?.tagName === 'SUMMARY' ? null : node?.closest('details');
          if (disclosure) {
            root.querySelectorAll('ep-control-surface details[open]').forEach(
              candidate => { if (candidate !== disclosure) candidate.open = false; }
            );
            disclosure.open = true;
          }
        }
        """,
        selector,
    )
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
          let flowParticleAnimations = 0;
          let otherAnimations = 0;
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
            const flowParticle = element.matches('.ep-v011-particles span');
            for (const pseudo of [null, '::before', '::after']) {
              const state = active(getComputedStyle(element, pseudo));
              if (state.hasAnimation) {
                animations += 1;
                if (flowParticle && pseudo === null) flowParticleAnimations += 1;
                else otherAnimations += 1;
              }
              if (state.hasTransition) transitions += 1;
              elementActive ||= state.hasAnimation || state.hasTransition;
            }
            if (elementActive) animatedElements += 1;
          }
          return {
            animations, transitions, animatedElements,
            flowParticleAnimations, otherAnimations,
          };
        }
        """
    )


def exercise_static_flow(page: Page) -> dict[str, object]:
    """Verify static direction, state, intensity, accessibility and DOM identity."""
    return page.evaluate(
        """
        async () => {
          const panel = window.__epPanel;
          const root = panel.shadowRoot;
          const selectors = {
            pv: '.ep-link-pv',
            grid: '.ep-link-grid',
            house: '.ep-link-house',
            battery: '.ep-link-battery',
          };
          const links = Object.fromEntries(
            Object.entries(selectors).map(([key, selector]) => [key, root.querySelector(selector)])
          );
          const arrows = Object.fromEntries(
            Object.entries(links).map(([key, link]) => [key, link?.querySelector('.ep-v041-flow-arrow')])
          );
          const main = root.querySelector('main');
          const overview = root.querySelector('.ep-flow-overview');
          const read = () => {
            const overviewRect = overview?.getBoundingClientRect();
            return Object.fromEntries(Object.entries(links).map(([key, link]) => {
              const arrow = link?.querySelector('.ep-v041-flow-arrow');
              const state = link?.querySelector('.ep-v041-flow-state');
              const track = link?.querySelector('.ep-flow-track');
              const arrowRect = arrow?.getBoundingClientRect();
              const vertical = key === 'house' || key === 'battery';
              const trackStyle = track ? getComputedStyle(track) : null;
              const arrowStyle = arrow ? getComputedStyle(arrow) : null;
              return [key, {
                status: link?.dataset.epV041FlowStatus || '',
                direction: link?.dataset.epV038Motion || '',
                intensity: link?.dataset.epV041FlowIntensity || '',
                role: link?.getAttribute('role') || '',
                label: link?.getAttribute('aria-label') || '',
                arrow: arrow?.textContent || '',
                arrowDisplay: arrow ? getComputedStyle(arrow).display : '',
                arrowBorder: arrowStyle?.borderStyle || '',
                arrowClipPath: arrowStyle?.clipPath || arrowStyle?.webkitClipPath || '',
                arrowFontSize: arrowStyle ? parseFloat(arrowStyle.fontSize) : -1,
                state: state?.textContent || '',
                stateDisplay: state ? getComputedStyle(state).display : '',
                thickness: trackStyle ? parseFloat(vertical ? trackStyle.width : trackStyle.height) : 0,
                trackMask: trackStyle?.maskImage || trackStyle?.webkitMaskImage || '',
                inside: Boolean(
                  overviewRect && arrowRect &&
                  arrowRect.left >= overviewRect.left - 1 &&
                  arrowRect.right <= overviewRect.right + 1 &&
                  arrowRect.top >= overviewRect.top - 1 &&
                  arrowRect.bottom <= overviewRect.bottom + 1
                ),
              }];
            }));
          };
          const settle = () => new Promise((resolve) => setTimeout(resolve, 180));
          const setInternalPv = (value) => {
            const numeric = Number(value);
            const available = value !== 'unknown' && Number.isFinite(numeric);
            window.__epSetEntityByKey('pv_total_power', value);
            window.__epSetEntityByKey('pv_generation_power', value, {
              internal_enabled: true,
              external_enabled: false,
              internal_power_w: available ? numeric : null,
              external_power_w: null,
              configured_external_sources: 0,
              available_external_sources: 0,
              sources: [{
                source_key: 'goodwe_internal',
                kind: 'internal',
                name: 'GoodWe PV',
                entity_id: null,
                power_w: available ? numeric : null,
                available,
              }],
            });
          };

          setInternalPv(4800);
          for (const [key, value] of [
            ['total_load_power', 2500],
            ['meter_total_power_fast', 1100],
            ['battery_power', -1200],
          ]) {
            window.__epSetEntityByKey(key, value);
          }
          await settle();
          const initial = read();
          window.__epSetEntityByKey('meter_total_power_fast', -650);
          window.__epSetEntityByKey('battery_power', 900);
          await settle();
          const reversed = read();

          setInternalPv('unknown');
          for (const key of ['total_load_power', 'meter_total_power_fast', 'battery_power']) {
            window.__epSetEntityByKey(key, 'unknown');
          }
          await settle();
          const unknown = read();

          setInternalPv(49);
          for (const [key, value] of [
            ['total_load_power', 49],
            ['meter_total_power_fast', -49],
            ['battery_power', 49],
          ]) {
            window.__epSetEntityByKey(key, value);
          }
          await settle();
          const idle = read();

          setInternalPv(4800);
          for (const [key, value] of [
            ['total_load_power', 2500],
            ['meter_total_power_fast', 1100],
            ['battery_power', -1200],
          ]) {
            window.__epSetEntityByKey(key, value);
          }
          await settle();
          const restored = read();

          return {
            initial,
            reversed,
            unknown,
            idle,
            restored,
            identity: {
              main: main === root.querySelector('main'),
              links: Object.entries(selectors).every(
                ([key, selector]) => links[key] === root.querySelector(selector)
              ),
              arrows: Object.entries(links).every(
                ([key, link]) => arrows[key] === link?.querySelector('.ep-v041-flow-arrow')
              ),
            },
            responsive: Boolean(
              overview && overview.scrollWidth <= overview.clientWidth + 1 &&
              overview.getBoundingClientRect().width <= window.__epScroller.clientWidth + 1
            ),
          };
        }
        """
    )


def exercise_connectivity_status(page: Page, profile: Profile) -> dict[str, object]:
    """Verify header placement, details, state changes and stable node identity."""
    enabled = EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS
    result: dict[str, object] = {
        "ran": enabled,
        "placed": False,
        "initial_ok": False,
        "details_open": False,
        "above_card_controls": False,
        "pointer_isolated": False,
        "hit_isolated": False,
        "issue_visible": False,
        "unknown_visible": False,
        "countdown_visible": False,
        "main_stable": False,
        "button_stable": False,
        "restored": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        initial = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const actions = root.querySelector('.header-actions');
              const wrap = root.querySelector('.ep-connectivity-wrap');
              const button = wrap?.querySelector('.ep-connectivity-status');
              window.__epConnectivityIdentity = {
                main: root.querySelector('main'),
                button,
              };
              const children = [...(actions?.children || [])];
              const index = children.indexOf(wrap);
              return {
                placed: index > 0 && children[index - 1]?.classList.contains('status') &&
                  children[index + 1]?.classList.contains('version'),
                label: button?.textContent?.trim() || '',
                ok: button?.classList.contains('ok') || false,
                aria: button?.getAttribute('aria-label') || '',
                rows: wrap?.querySelectorAll('.ep-connectivity-row').length || 0,
              };
            }
            """
        )
        result["placed"] = initial["placed"]
        result["initial_ok"] = (
            initial["label"] == "ALL OK"
            and initial["ok"]
            and "System status" in initial["aria"]
            and initial["rows"] == 3
        )

        activate(page, profile, ".ep-connectivity-status")
        opened = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const button = root.querySelector('.ep-connectivity-status');
              const popover = root.querySelector('.ep-connectivity-popover');
              const cardControls = root.querySelector('.ep-v031-card-windowbar');
              const popoverStyle = popover ? getComputedStyle(popover) : null;
              const controlsStyle = cardControls ? getComputedStyle(cardControls) : null;
              const rect = popover?.getBoundingClientRect();
              const hit = rect
                ? root.elementFromPoint(
                    rect.left + rect.width / 2,
                    rect.top + rect.height / 2
                  )
                : null;
              return {
                open: button?.getAttribute('aria-expanded') === 'true' &&
                  popoverStyle?.display === 'block',
                aboveCardControls:
                  Number(popoverStyle?.zIndex) > Number(controlsStyle?.zIndex),
                pointerIsolated: popoverStyle?.pointerEvents !== 'none',
                hitIsolated: Boolean(
                  hit && popover && (hit === popover || popover.contains(hit))
                ),
              };
            }
            """
        )
        result["details_open"] = opened["open"]
        result["above_card_controls"] = opened["aboveCardControls"]
        result["pointer_isolated"] = opened["pointerIsolated"]
        result["hit_isolated"] = opened["hitIsolated"]

        page.evaluate(
            """
            () => window.__epSetEntityByKey('connectivity_status', 'issue', {
              modbus_status: 'online',
              refresh_seconds: 15,
              ev_status: 'unreachable',
              ev_coordination_requested: true,
              ev_coordination_effective: true,
              ev_coordination_suspended: false,
              ev_transition: 'suspend_pending',
              ev_transition_remaining_seconds: 165,
            })
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-connectivity-status'
            )?.classList.contains('issue')
            """,
            timeout=5_000,
        )
        issue = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const button = root.querySelector('.ep-connectivity-status');
              const ev = root.querySelector('[data-connectivity-row="ev"]');
              const coordination = root.querySelector(
                '[data-connectivity-row="coordination"]'
              );
              return {
                label: button?.textContent?.trim() || '',
                issue: button?.classList.contains('issue') || false,
                unknown: ev?.textContent?.includes('Unknown / unreachable') || false,
                countdown: coordination?.textContent?.includes('pauses in 2m 45s') || false,
                main: window.__epConnectivityIdentity.main === root.querySelector('main'),
                buttonStable: window.__epConnectivityIdentity.button === button,
              };
            }
            """
        )
        result["issue_visible"] = issue["label"] == "ISSUE" and issue["issue"]
        result["unknown_visible"] = issue["unknown"]
        result["countdown_visible"] = issue["countdown"]
        result["main_stable"] = issue["main"]
        result["button_stable"] = issue["buttonStable"]

        page.evaluate(
            """
            () => window.__epSetEntityByKey('connectivity_status', 'all_ok', {
              modbus_status: 'online',
              refresh_seconds: 15,
              ev_status: 'online',
              ev_coordination_requested: true,
              ev_coordination_effective: true,
              ev_coordination_suspended: false,
              ev_transition: null,
              ev_transition_remaining_seconds: null,
            })
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-connectivity-status'
            )?.classList.contains('ok')
            """,
            timeout=5_000,
        )
        result["restored"] = True
    except (PlaywrightError, RuntimeError) as err:
        result["error"] = str(err)
    return result


def open_and_close_menu(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "open": False,
        "close": False,
        "motion_available": False,
        "motion_default_on": False,
        "motion_off": False,
        "motion_on": False,
        "motion_reduced": False,
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
        if EXPECTED_ENTRYPOINT not in STABLE_ENTRYPOINTS:
            close = shadow(page, ".ep-menu-close")
            close.click(timeout=5_000)
            page.wait_for_function(
                "() => !window.__epPanel.shadowRoot.querySelector('.ep-layout-menu')",
                timeout=5_000,
            )
            result["close"] = True
            return result
        result["motion_available"] = page.evaluate(
            """
            () => {
              const input = window.__epPanel.shadowRoot.querySelector('[data-ep-setting="animations"]');
              return Boolean(input && !input.disabled && input.getAttribute('aria-disabled') !== 'true');
            }
            """
        )
        result["motion_default_on"] = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const input = root.querySelector('[data-ep-setting="animations"]');
              const layout = root.querySelector('.ep-dashboard-layout');
              return Boolean(input?.checked && !layout?.classList.contains('ep-animations-off'));
            }
            """
        )
        motion_input = shadow(page, '[data-ep-setting="animations"]')
        motion_input.uncheck(timeout=5_000)
        page.wait_for_function(
            "() => window.__epPanel.shadowRoot.querySelector('.ep-dashboard-layout')?.classList.contains('ep-animations-off')",
            timeout=5_000,
        )
        off_summary = animation_summary(page)
        result["motion_off_summary"] = off_summary
        result["motion_off"] = (
            off_summary["flowParticleAnimations"] == 0
            and off_summary["otherAnimations"] == 0
            and off_summary["transitions"] == 0
        )

        motion_input = shadow(page, '[data-ep-setting="animations"]')
        motion_input.check(timeout=5_000)
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-dashboard-layout')?.classList.contains('ep-animations-off')",
            timeout=5_000,
        )
        on_summary = animation_summary(page)
        result["motion_on_summary"] = on_summary
        result["motion_on"] = (
            on_summary["flowParticleAnimations"] > 0
            and on_summary["otherAnimations"] == 0
            and on_summary["transitions"] == 0
        )

        page.emulate_media(reduced_motion="reduce")
        page.wait_for_function(
            """
            () => [...window.__epPanel.shadowRoot.querySelectorAll('.ep-v011-particles span')]
              .every((particle) => getComputedStyle(particle).animationName === 'none')
            """,
            timeout=5_000,
        )
        reduced_summary = animation_summary(page)
        result["motion_reduced_summary"] = reduced_summary
        result["motion_reduced"] = (
            reduced_summary["animations"] == 0
            and reduced_summary["transitions"] == 0
        )
        page.emulate_media(reduced_motion="no-preference")
        page.wait_for_function(
            """
            () => [...window.__epPanel.shadowRoot.querySelectorAll('.ep-v011-particles span')]
              .some((particle) => getComputedStyle(particle).animationName !== 'none')
            """,
            timeout=5_000,
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


def exercise_setpoint_update(page: Page) -> dict[str, object]:
    """Keep the Controller DOM stable while its persisted write time advances."""
    try:
        return page.evaluate(
            """
            async () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const metric = [...root.querySelectorAll('.panel-card.controller .metric')].find(
                node => ['EMS setpoint', 'EMS-setpoint'].includes(
                  node.querySelector('.metric-label')?.textContent?.trim()
                )
              );
              const main = root.querySelector('main');
              const sub = metric?.querySelector('.metric-sub');
              const before = sub?.textContent || '';
              window.__epSetEntityByKey('control_command', 'battery_charge', {
                last_ems_setpoint_updated_at: '2026-08-29T18:30:45+00:00',
                last_ems_setpoint: 1200,
                last_ems_mode: 11,
                last_ems_setpoint_command: 'battery_charge',
              });
              for (let attempt = 0; attempt < 40; attempt += 1) {
                if (sub?.textContent !== before) break;
                await new Promise(resolve => setTimeout(resolve, 20));
              }
              return {
                present: Boolean(sub && before.includes('Last update:')),
                changed: Boolean(sub && sub.textContent !== before),
                stableMain: root.querySelector('main') === main,
                stableMetric: [...root.querySelectorAll('.panel-card.controller .metric')].includes(metric),
                value: sub?.textContent || '',
              };
            }
            """
        )
    except PlaywrightError as err:
        return {
            "present": False,
            "changed": False,
            "stableMain": False,
            "stableMetric": False,
            "value": "",
            "error": str(err),
        }


def exercise_emhass_mapping(page: Page) -> dict[str, object]:
    """Use the backend decision instead of reinterpreting P_batt in the UI."""
    if EXPECTED_ENTRYPOINT not in STABLE_ENTRYPOINTS:
        return {"ran": False, "mode1": False, "mode10": False, "stable": False}
    try:
        return page.evaluate(
            """
            async () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const metric = [...root.querySelectorAll('.panel-card.emhass .metric')].find(
                node => ['Mapping', 'Toewijzing', 'Aansturing'].includes(
                  node.querySelector('.metric-label')?.textContent?.trim()
                )
              );
              const value = metric?.querySelector('.metric-value');
              const main = root.querySelector('main');
              const settle = () => new Promise(resolve => setTimeout(resolve, 180));
              const setDecision = (command, mode, target, pBatt, pGrid) => {
                window.__epSetEntity('sensor.p_batt_forecast', pBatt, {
                  unit_of_measurement: 'W',
                });
                window.__epSetEntity('sensor.p_grid_forecast', pGrid, {
                  unit_of_measurement: 'W',
                });
                window.__epSetEntityByKey('optimize_now', 'unknown', {
                  controller_enabled: true,
                  controller_command: command,
                  controller_expected_mode: mode,
                  controller_target_power: target,
                  p_batt_value: pBatt,
                  p_grid_value: pGrid,
                });
              };

              setDecision('hybrid_grid_zero_auto', 1, 0, 775, 0);
              await settle();
              const mode1 = value?.textContent?.trim() || '';

              setDecision('hybrid_grid_export', 10, 14128, 15000, -14128);
              await settle();
              const mode10 = value?.textContent?.trim() || '';

              setDecision('battery_charge', 11, -1200, -1200, 1100);
              await settle();
              return {
                ran: true,
                mode1: mode1 === 'Mode 1 · GoodWe Auto / AI',
                mode10: mode10 === 'Mode 10 · Grid export target · 14.1 kW',
                stable: root.querySelector('main') === main &&
                  [...root.querySelectorAll('.panel-card.emhass .metric')].includes(metric),
              };
            }
            """
        )
    except PlaywrightError as err:
        return {
            "ran": True,
            "mode1": False,
            "mode10": False,
            "stable": False,
            "error": str(err),
        }


def exercise_automatic_control(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "present": False,
        "compact_on": False,
        "off_changed": False,
        "controls_shown_off": False,
        "off_nodes_stable": False,
        "on_changed": False,
        "compact_restored_on": False,
        "on_nodes_stable": False,
        "manual_mode_worked": False,
        "focus_rehomed": False,
        "final_on": False,
        "main_stable": False,
        "error": None,
    }
    try:
        auto = shadow(page, "#auto-toggle")
        auto.scroll_into_view_if_needed(timeout=5_000)
        result["present"] = auto.count() == 1
        page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              window.__epAutoMain = root.querySelector('main');
              window.__epManualIdentity = {
                pad: root.querySelector('.ep-v021-manual-pad'),
                grid: root.querySelector('.ep-v021-mode-grid'),
                power: root.querySelector('.ep-v021-power-row'),
                mode: root.querySelector('.ep-v021-mode-button[data-mode="8"]'),
                slider: root.querySelector('.ep-v021-power-slider'),
              };
            }
            """
        )
        result["compact_on"] = page.evaluate(
            """
            () => {
              const identity = window.__epManualIdentity;
              return Boolean(
                identity.pad?.classList.contains('compact') &&
                identity.grid?.hidden && identity.power?.hidden &&
                identity.mode?.disabled && identity.slider?.disabled &&
                identity.pad?.querySelector('[data-manual-note]')?.textContent.includes(
                  'Automatic Control owns the inverter.'
                )
              );
            }
            """
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
        page.wait_for_function(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              return !root.querySelector('.ep-v021-manual-pad')?.classList.contains('compact') &&
                !root.querySelector('.ep-v021-mode-grid')?.hidden &&
                !root.querySelector('.ep-v021-power-row')?.hidden;
            }
            """,
            timeout=5_000,
        )
        off_state = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const identity = window.__epManualIdentity;
              const pad = root.querySelector('.ep-v021-manual-pad');
              const grid = root.querySelector('.ep-v021-mode-grid');
              const power = root.querySelector('.ep-v021-power-row');
              const mode = root.querySelector('.ep-v021-mode-button[data-mode="8"]');
              const slider = root.querySelector('.ep-v021-power-slider');
              return {
                shown: Boolean(
                  pad && !pad.classList.contains('compact') &&
                  grid && !grid.hidden && power && !power.hidden &&
                  mode && !mode.disabled && mode.getAttribute('aria-disabled') === 'false' &&
                  slider && !slider.disabled &&
                  pad.querySelector('[data-manual-note]')?.textContent.trim().startsWith('Live:')
                ),
                stable: Boolean(
                  identity.pad === pad && identity.grid === grid &&
                  identity.power === power && identity.mode === mode &&
                  identity.slider === slider
                ),
              };
            }
            """
        )
        result["controls_shown_off"] = off_state["shown"]
        result["off_nodes_stable"] = off_state["stable"]

        auto = shadow(page, "#auto-toggle")
        auto.click(timeout=5_000)
        page.wait_for_function(
            """
            entityId => {
              const root = window.__epPanel.shadowRoot;
              return window.__epHass.states[entityId]?.state === 'on' &&
                root.querySelector('.ep-v021-manual-pad')?.classList.contains('compact') &&
                root.querySelector('.ep-v021-mode-grid')?.hidden &&
                root.querySelector('.ep-v021-power-row')?.hidden;
            }
            """,
            arg=automatic_id,
            timeout=5_000,
        )
        result["on_changed"] = True
        on_state = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const identity = window.__epManualIdentity;
              const pad = root.querySelector('.ep-v021-manual-pad');
              const grid = root.querySelector('.ep-v021-mode-grid');
              const power = root.querySelector('.ep-v021-power-row');
              const mode = root.querySelector('.ep-v021-mode-button[data-mode="8"]');
              const slider = root.querySelector('.ep-v021-power-slider');
              return {
                compact: Boolean(
                  pad?.classList.contains('compact') && grid?.hidden &&
                  power?.hidden && mode?.disabled && slider?.disabled
                ),
                stable: Boolean(
                  identity.pad === pad && identity.grid === grid &&
                  identity.power === power && identity.mode === mode &&
                  identity.slider === slider
                ),
              };
            }
            """
        )
        result["compact_restored_on"] = on_state["compact"]
        result["on_nodes_stable"] = on_state["stable"]
        result["main_stable"] = page.evaluate(
            "window.__epAutoMain === window.__epPanel.shadowRoot.querySelector('main')"
        )

        auto = shadow(page, "#auto-toggle")
        auto.click(timeout=5_000)
        page.wait_for_function(
            """
            entityId => {
              const root = window.__epPanel.shadowRoot;
              return window.__epHass.states[entityId]?.state === 'off' &&
                !root.querySelector('.ep-v021-manual-pad')?.classList.contains('compact') &&
                !root.querySelector('.ep-v021-mode-grid')?.hidden &&
                !root.querySelector('.ep-v021-power-row')?.hidden;
            }
            """,
            arg=automatic_id,
            timeout=5_000,
        )
        manual_mode_id = page.evaluate(
            "window.__epPanel._entityId('manual_mode')"
        )
        manual_calls_before = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.domain === 'select' && call.service === 'select_option' &&
                call.data?.entity_id === entityId
            ).length
            """,
            manual_mode_id,
        )
        mode_eight = shadow(page, '.ep-v021-mode-button[data-mode="8"]')
        mode_eight.evaluate(
            "node => { const disclosure = node.closest('details'); if (disclosure) disclosure.open = true; }"
        )
        mode_eight.click(timeout=5_000)
        page.wait_for_function(
            """
            ([entityId, expected]) => window.__epServiceCalls.filter(
              call => call.domain === 'select' && call.service === 'select_option' &&
                call.data?.entity_id === entityId && call.data?.option?.startsWith('8:')
            ).length === expected
            """,
            arg=[manual_mode_id, manual_calls_before + 1],
            timeout=5_000,
        )
        result["manual_mode_worked"] = True

        wait_render_idle(page)
        mode_eight = shadow(page, '.ep-v021-mode-button[data-mode="8"]')
        mode_eight.focus(timeout=5_000)
        page.evaluate(
            "window.__epSetEntityByKey('automatic_control', 'on')"
        )
        page.wait_for_function(
            """
            entityId => {
              const root = window.__epPanel.shadowRoot;
              return window.__epHass.states[entityId]?.state === 'on' &&
                root.querySelector('.ep-v021-manual-pad')?.classList.contains('compact') &&
                root.querySelector('.ep-v021-mode-grid')?.hidden &&
                root.querySelector('.ep-v021-power-row')?.hidden;
            }
            """,
            arg=automatic_id,
            timeout=5_000,
        )
        result["focus_rehomed"] = page.evaluate(
            """
            () => window.__epPanel.shadowRoot.activeElement ===
              window.__epPanel.shadowRoot.querySelector('#auto-toggle')
            """
        )
        result["final_on"] = page.evaluate(
            """
            entityId => {
              const root = window.__epPanel.shadowRoot;
              return window.__epHass.states[entityId]?.state === 'on' &&
                root.querySelector('.ep-v021-manual-pad')?.classList.contains('compact') &&
                root.querySelector('.ep-v021-mode-grid')?.hidden &&
                root.querySelector('.ep-v021-power-row')?.hidden;
            }
            """,
            automatic_id,
        )
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_strategy_note_stability(page: Page) -> dict[str, object]:
    """Keep the v0.48 Hybrid explanation stable across telemetry patches."""
    result: dict[str, object] = {
        "ran": False,
        "present": False,
        "note_stable": False,
        "strong_stable": False,
        "height_stable": False,
        "no_child_rebuilds": False,
        "dutch_copy": False,
        "context_refresh": False,
        "error": None,
    }
    if EXPECTED_ENTRYPOINT not in {"v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}:
        return result
    try:
        state = page.evaluate(
            """
            async () => {
              const waitForStrategyLanguage = async (language) => {
                const expectedKey = `${language}:hybrid`;
                const deadline = performance.now() + 3_000;
                while (performance.now() < deadline) {
                  const note = window.__epPanel.shadowRoot.querySelector(
                    '.ep-v022-strategy-note'
                  );
                  if (note?.dataset.epV048PresentationKey === expectedKey) {
                    return note;
                  }
                  await new Promise((resolve) => setTimeout(resolve, 20));
                }
                return window.__epPanel.shadowRoot.querySelector(
                  '.ep-v022-strategy-note'
                );
              };
              window.__epSetLanguage('nl');
              await waitForStrategyLanguage('nl');
              const root = window.__epPanel.shadowRoot;
              const note = root.querySelector('.ep-v022-strategy-note');
              const strong = note?.querySelector('strong');
              if (!note || !strong) return { present: false };
              const initialHeight = note.getBoundingClientRect().height;
              let childRebuilds = 0;
              const observer = new MutationObserver((mutations) => {
                childRebuilds += mutations.filter(
                  (mutation) => mutation.type === 'childList'
                ).length;
              });
              observer.observe(note, { childList: true, subtree: true });
              await window.__epTelemetryBurst(60, 4);
              await new Promise((resolve) => setTimeout(resolve, 180));
              observer.disconnect();
              const liveRoot = window.__epPanel.shadowRoot;
              const liveNote = liveRoot.querySelector('.ep-v022-strategy-note');
              const liveStrong = liveNote?.querySelector('strong');
              const liveHeight = liveNote?.getBoundingClientRect().height;
              const dutchCopy = liveNote?.textContent?.includes(
                'Automatische regelstrategie:'
              ) && liveNote?.textContent?.includes('Hybride regeling');
              const stable = {
                present: true,
                noteStable: note === liveNote,
                strongStable: strong === liveStrong,
                heightStable: Math.abs(initialHeight - liveHeight) <= 0.5,
                noChildRebuilds: childRebuilds === 0,
                dutchCopy: Boolean(dutchCopy),
              };
              window.__epSetLanguage('en');
              const englishNote = await waitForStrategyLanguage('en');
              return {
                ...stable,
                contextRefresh:
                  englishNote?.dataset.epV048PresentationKey === 'en:hybrid' &&
                  englishNote?.textContent?.includes('Automatic control strategy:'),
              };
            }
            """
        )
        result.update({
            "ran": True,
            "present": state.get("present", False),
            "note_stable": state.get("noteStable", False),
            "strong_stable": state.get("strongStable", False),
            "height_stable": state.get("heightStable", False),
            "no_child_rebuilds": state.get("noChildRebuilds", False),
            "dutch_copy": state.get("dutchCopy", False),
            "context_refresh": state.get("contextRefresh", False),
        })
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_ev_protection_banner(page: Page) -> dict[str, object]:
    """Verify EV status patches one stable, non-interactive controller banner."""
    result: dict[str, object] = {
        "present": False,
        "initial_hidden": False,
        "blocking": False,
        "allowing": False,
        "waiting": False,
        "inactive_hidden": False,
        "main_stable": False,
        "banner_stable": False,
        "non_interactive": False,
        "error": None,
    }
    try:
        banner = page.locator("gw-energypilot-panel").locator(
            ".ep-v041-ev-protection"
        )
        if banner.count() != 1:
            return result
        result["present"] = True
        initial = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              window.__epEvIdentity = {
                main: root.querySelector('main'),
                banner: root.querySelector('.ep-v041-ev-protection'),
              };
              return window.__epEvIdentity.banner.hidden;
            }
            """
        )
        result["initial_hidden"] = initial

        page.evaluate(
            """
            window.__epSetEntityByKey('control_command', 'ev_anti_discharge_hold', {
              ev_active: true,
              ev_protection_state: 'blocking_discharge',
            })
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v041-ev-protection[data-state="blocking_discharge"]:not([hidden])'
            )
            """
        )
        blocking = page.evaluate(
            """
            () => {
              const banner = window.__epPanel.shadowRoot.querySelector('.ep-v041-ev-protection');
              return {
                title: banner.querySelector('.ep-v041-ev-title')?.textContent?.trim(),
                detail: banner.querySelector('.ep-v041-ev-detail')?.textContent?.trim(),
              };
            }
            """
        )
        result["blocking"] = blocking == {
            "title": "EV CHARGING · ANTI-DISCHARGE ACTIVE",
            "detail": "Home battery discharge is blocked · Mode 8 Battery Hold",
        }

        page.evaluate(
            """
            window.__epSetEntityByKey('control_command', 'ev_battery_charge', {
              ev_active: true,
              ev_protection_state: 'allowing_charge',
            })
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v041-ev-protection[data-state="allowing_charge"]:not([hidden])'
            )
            """
        )
        result["allowing"] = page.evaluate(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v041-ev-title'
            )?.textContent?.trim() === 'EV CHARGING · BATTERY CHARGE ALLOWED'
            """
        )

        page.evaluate(
            """
            window.__epSetEntityByKey('control_command', 'waiting_for_ev_stop_optimization', {
              ev_active: false,
              ev_protection_state: 'waiting_for_fresh_plan',
            })
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v041-ev-protection[data-state="waiting_for_fresh_plan"]:not([hidden])'
            )
            """
        )
        result["waiting"] = page.evaluate(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v041-ev-title'
            )?.textContent?.trim() === 'EV CHARGING STOPPED · FRESH PLAN REQUIRED'
            """
        )

        page.evaluate(
            """
            window.__epSetEntityByKey('control_command', 'battery_charge', {
              ev_active: false,
              ev_protection_state: 'inactive',
            })
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v041-ev-protection'
            )?.hidden === true
            """
        )
        stable = page.evaluate(
            """
            async () => {
              await window.__epTelemetryBurst(20, 4);
              await new Promise((resolve) => setTimeout(resolve, 150));
              const root = window.__epPanel.shadowRoot;
              const banner = root.querySelector('.ep-v041-ev-protection');
              return {
                inactiveHidden: banner.hidden,
                mainStable: window.__epEvIdentity.main === root.querySelector('main'),
                bannerStable: window.__epEvIdentity.banner === banner,
                nonInteractive: banner.querySelectorAll('button, a, input, select').length === 0,
              };
            }
            """
        )
        result["inactive_hidden"] = stable["inactiveHidden"]
        result["main_stable"] = stable["mainStable"]
        result["banner_stable"] = stable["bannerStable"]
        result["non_interactive"] = stable["nonInteractive"]
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_strategy(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "present": False,
        "changed": False,
        "message": "",
        "profile_choices": 0,
        "chargegasm_present": False,
        "managed_summary": False,
        "custom_sliders_absent": False,
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
        button.evaluate(
            "node => { const disclosure = node.closest('details'); if (disclosure) disclosure.open = true; }"
        )
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
        policy = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              return {
                profileChoices: root.querySelectorAll('[data-ep-v038-profile]').length,
                chargegasmPresent: Boolean(
                  root.querySelector('[data-ep-v038-profile="chargegasm"]')
                ),
                managedSummary: Boolean(
                  root.querySelector('.ep-v038-managed')?.textContent.includes('5%') &&
                  root.querySelector('.ep-v038-managed')?.textContent.includes('100%')
                ),
                customSlidersAbsent: !root.querySelector('input[data-ep-v038-soc]'),
              };
            }
            """
        )
        result["profile_choices"] = policy["profileChoices"]
        result["chargegasm_present"] = policy["chargegasmPresent"]
        result["managed_summary"] = policy["managedSummary"]
        result["custom_sliders_absent"] = policy["customSlidersAbsent"]
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_soc_slider_draft(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "present": False,
        "slider_kept_draft": False,
        "label_kept_draft": False,
        "acknowledged": False,
        "custom_values_saved": False,
        "custom_main_stable": False,
        "custom_typography_larger": False,
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
        custom = page.evaluate(
            """
            async () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const main = root.querySelector('main');
              const form = root.querySelector('[data-ep-v038-custom-form]');
              const requested = {
                battery_soc_deficit_cost: 0.001111,
                battery_soc_surplus_cost: 0.002222,
                battery_stress_cost: 0.003333,
                weight_battery_charge: 0.004444,
                weight_battery_discharge: 0.005555,
              };
              for (const [key, value] of Object.entries(requested)) {
                const input = form?.querySelector(`[data-ep-v038-custom-value="${key}"]`);
                if (input) input.value = String(value);
              }
              const titleSize = parseFloat(getComputedStyle(
                root.querySelector('.ep-v038-profile strong')
              ).fontSize);
              const descriptionSize = parseFloat(getComputedStyle(
                root.querySelector('.ep-v038-profile small')
              ).fontSize);
              form?.dispatchEvent(new Event('submit', { bubbles: true, composed: true, cancelable: true }));
              await new Promise((resolve) => setTimeout(resolve, 160));
              const call = [...window.__epWsCalls].reverse().find(
                item => item.type === 'gw_energypilot/battery_saver/custom_set'
              );
              return {
                requested,
                submitted: call?.values || null,
                managed: panel.__epV038BatterySaver?.data?.managed,
                mainStable: main === root.querySelector('main'),
                titleSize,
                descriptionSize,
              };
            }
            """
        )
        result["custom_values_saved"] = (
            custom["submitted"] == custom["requested"] and custom["managed"] is False
        )
        result["custom_main_stable"] = custom["mainStable"]
        result["custom_typography_larger"] = (
            custom["titleSize"] >= 12 and custom["descriptionSize"] >= 9
        )
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_emhass_overview_controls(page: Page) -> dict[str, object]:
    """Keep SOC writes single-owner and mirror confirmed overview costfun state."""
    return page.evaluate(
        """
        async () => {
          const panel = window.__epPanel;
          const root = panel.shadowRoot;
          const originalNarrow = panel.narrow;
          const costfunId = panel._entityId('emhass_cost_function');
          window.__epSetEntityByKey('emhass_minimum_soc', 'unknown');
          window.__epSetEntityByKey('emhass_maximum_soc', 'unknown');

          // A genuine context change runs every historical structural creator.
          // The permanent-control guard must still suppress the old sliders.
          panel.narrow = !originalNarrow;
          await new Promise((resolve) => setTimeout(resolve, 220));
          const card = root.querySelector('.panel-card.emhass');
          const legacySocCount = card?.querySelectorAll('input[data-soc-slider]').length ?? -1;
          const permanentSocCount = root.querySelectorAll(
            'ep-battery-strategy [data-control-id="profile:minimum-soc"], ' +
            'ep-battery-strategy [data-control-id="profile:maximum-soc"]'
          ).length;

          window.__epSetEntity(costfunId, 'Profit', {emhass_costfun: 'profit'});
          await new Promise((resolve) => setTimeout(resolve, 120));
          const profit = [...card.querySelectorAll('button[data-emhass-overview-costfun]')]
            .filter((button) => button.getAttribute('aria-pressed') === 'true')
            .map((button) => button.dataset.emhassOverviewCostfun);

          window.__epSetEntity(costfunId, 'Cost', {emhass_costfun: 'cost'});
          await new Promise((resolve) => setTimeout(resolve, 120));
          const cost = [...card.querySelectorAll('button[data-emhass-overview-costfun]')]
            .filter((button) => button.getAttribute('aria-pressed') === 'true')
            .map((button) => button.dataset.emhassOverviewCostfun);

          window.__epSetEntityByKey('emhass_minimum_soc', 5);
          window.__epSetEntityByKey('emhass_maximum_soc', 95);
          window.__epSetEntity(costfunId, 'Profit', {emhass_costfun: 'profit'});
          panel.narrow = originalNarrow;
          await new Promise((resolve) => setTimeout(resolve, 220));
          return {
            legacySocCount,
            permanentSocCount,
            profit,
            cost,
            restoredLegacySocCount:
              root.querySelector('.panel-card.emhass')
                ?.querySelectorAll('input[data-soc-slider]').length ?? -1,
          };
        }
        """
    )


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


def exercise_host_property_press(page: Page, profile: Profile) -> dict[str, object]:
    """Emulate Home Assistant host assignments during one physical press."""
    enabled = EXPECTED_ENTRYPOINT in {"v045", "v046", "v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "no_full_render": False,
        "main_stable": False,
        "controls_stable": False,
        "native_click": False,
        "touch_click": False,
        "real_panel_change": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        wait_render_idle(page)
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              window.__epIssue84Identity = {
                main: root.querySelector('main'),
                optimize: root.querySelector('.ep-optimize-now'),
                quick: root.querySelector('[data-action="max_charge"]'),
                layout: root.querySelector('.ep-layout-button'),
              };
              window.__epIssue84RenderCount = 0;
              window.__epIssue84OriginalRender = panel._render;
              panel._render = function issue84HostRenderProbe(...args) {
                window.__epIssue84RenderCount += 1;
                return window.__epIssue84OriginalRender.apply(this, args);
              };
            }
            """
        )
        host_stability = page.evaluate(
            """
            async () => {
              const panel = window.__epPanel;
              for (let index = 0; index < 40; index += 1) {
                window.__epSetEntityByKey('battery_power', index % 2 ? 925 : -1175);
                panel.narrow = panel.narrow;
                panel.panel = JSON.parse(JSON.stringify(panel.panel));
                await new Promise((resolve) => setTimeout(resolve, 4));
              }
              await new Promise((resolve) => setTimeout(resolve, 120));
              const root = panel.shadowRoot;
              return {
                renders: window.__epIssue84RenderCount,
                main: window.__epIssue84Identity.main === root.querySelector('main'),
                controls: [
                  ['optimize', '.ep-optimize-now'],
                  ['quick', '[data-action="max_charge"]'],
                  ['layout', '.ep-layout-button'],
                ].every(([key, selector]) =>
                  window.__epIssue84Identity[key] === root.querySelector(selector)
                ),
              };
            }
            """
        )
        result["no_full_render"] = host_stability["renders"] == 0
        result["main_stable"] = host_stability["main"]
        result["controls_stable"] = host_stability["controls"]

        optimize_id = page.evaluate("window.__epPanel._entityId('optimize_now')")
        optimize_before = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.data?.entity_id === entityId
            ).length
            """,
            optimize_id,
        )
        optimize = shadow(page, ".ep-optimize-now")
        optimize.scroll_into_view_if_needed(timeout=5_000)
        optimize_box = optimize.bounding_box()
        if optimize_box is None:
            raise RuntimeError("Optimize now has no hit area")
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              panel.shadowRoot.addEventListener('pointerdown', () => {
                panel.narrow = panel.narrow;
                panel.panel = JSON.parse(JSON.stringify(panel.panel));
              }, {capture: true, once: true});
            }
            """
        )
        optimize_x = optimize_box["x"] + optimize_box["width"] / 2
        optimize_y = optimize_box["y"] + optimize_box["height"] / 2
        page.mouse.move(optimize_x, optimize_y)
        page.mouse.down()
        page.wait_for_timeout(80)
        page.mouse.up()
        wait_service_count(page, optimize_id, optimize_before + 1)
        result["native_click"] = page.evaluate(
            """
            () => window.__epIssue84Identity.optimize ===
              window.__epPanel.shadowRoot.querySelector('.ep-optimize-now')
            """
        )
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-optimize-now')?.disabled",
            timeout=10_000,
        )

        quick_id = page.evaluate("window.__epPanel._entityId('max_charge')")
        quick_before = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.data?.entity_id === entityId
            ).length
            """,
            quick_id,
        )
        quick = shadow(page, '[data-action="max_charge"]')
        quick.scroll_into_view_if_needed(timeout=5_000)
        quick_box = quick.bounding_box()
        if quick_box is None:
            raise RuntimeError("Max charge has no hit area")
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              window.__epIssue84HostChurn = (async () => {
                for (let index = 0; index < 50; index += 1) {
                  panel.narrow = panel.narrow;
                  panel.panel = JSON.parse(JSON.stringify(panel.panel));
                  await new Promise((resolve) => setTimeout(resolve, 3));
                }
              })();
            }
            """
        )
        page.wait_for_timeout(12)
        quick_x = quick_box["x"] + quick_box["width"] / 2
        quick_y = quick_box["y"] + quick_box["height"] / 2
        if profile.touch:
            page.touchscreen.tap(quick_x, quick_y)
        else:
            page.mouse.click(quick_x, quick_y)
        wait_service_count(page, quick_id, quick_before + 1)
        page.evaluate("window.__epIssue84HostChurn")
        result["touch_click"] = True
        page.evaluate(
            """
            () => {
              window.__epSetEntityByKey('control_command', 'battery_charge');
              window.__epSetEntityByKey('automatic_control', 'on');
            }
            """
        )
        wait_render_idle(page)
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              window.__epIssue84StructuralMain = panel.shadowRoot.querySelector('main');
              window.__epIssue84StructuralSurface = panel.shadowRoot.querySelector('ep-control-surface');
              window.__epIssue84StructuralRenders = window.__epIssue84RenderCount;
              const nextPanel = JSON.parse(JSON.stringify(panel.panel));
              nextPanel.config = {
                ...(nextPanel.config || {}),
                issue84StructuralProbe: 'changed',
              };
              panel.panel = nextPanel;
            }
            """
        )
        page.wait_for_function(
            """
            () => window.__epIssue84RenderCount > window.__epIssue84StructuralRenders && (
              window.__epPanel.__epControlSurfaceArchitecture
                ? window.__epPanel.shadowRoot.querySelector('main') ===
                    window.__epIssue84StructuralMain &&
                  window.__epPanel.shadowRoot.querySelector('ep-control-surface') ===
                    window.__epIssue84StructuralSurface
                : window.__epPanel.shadowRoot.querySelector('main') !==
                    window.__epIssue84StructuralMain
            )
            """,
            timeout=5_000,
        )
        wait_render_idle(page)
        structural = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              return {
                renders:
                  window.__epIssue84RenderCount - window.__epIssue84StructuralRenders,
                rebuilt:
                  window.__epIssue84StructuralMain !==
                    panel.shadowRoot.querySelector('main'),
                declarativeStable:
                  window.__epIssue84StructuralMain === panel.shadowRoot.querySelector('main') &&
                  window.__epIssue84StructuralSurface ===
                    panel.shadowRoot.querySelector('ep-control-surface'),
                architecture: Boolean(panel.__epControlSurfaceArchitecture),
              };
            }
            """
        )
        result["real_panel_change"] = (
            structural["renders"] == 1
            and (
                structural["declarativeStable"]
                if structural["architecture"]
                else structural["rebuilt"]
            )
        )
    except (PlaywrightError, RuntimeError) as err:
        result["error"] = str(err)
    finally:
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              if (window.__epIssue84OriginalRender) {
                panel._render = window.__epIssue84OriginalRender;
              }
            }
            """
        )
    return result


def exercise_live_copy_press(page: Page, profile: Profile) -> dict[str, object]:
    """Keep WebKit's native click alive while live patches refresh button copy."""
    enabled = EXPECTED_ENTRYPOINT in {"v101", "v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "optimize_click": False,
        "costfun_click": False,
        "optimize_copy_stable": False,
        "costfun_copy_stable": False,
        "no_full_render": False,
        "main_stable": False,
        "controls_stable": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        wait_render_idle(page)
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              window.__epIssue110Identity = {
                main: root.querySelector('main'),
                optimize: root.querySelector('.ep-optimize-now'),
                costfun: root.querySelector('[data-costfun="cost"]'),
              };
              window.__epIssue110RenderCount = 0;
              window.__epIssue110OriginalRender = panel._render;
              panel._render = function issue110RenderProbe(...args) {
                window.__epIssue110RenderCount += 1;
                return window.__epIssue110OriginalRender.apply(this, args);
              };
              window.__epSetEntity(
                panel._entityId('emhass_cost_function'),
                'Profit',
                {emhass_costfun: 'profit'}
              );
            }
            """
        )
        page.wait_for_timeout(120)

        for name, selector, entity_key in (
            ("optimize", ".ep-optimize-now", "optimize_now"),
            ("costfun", '[data-costfun="cost"]', "emhass_cost_function"),
        ):
            entity_id = page.evaluate(
                "key => window.__epPanel._entityId(key)", entity_key
            )
            before = page.evaluate(
                """
                entityId => window.__epServiceCalls.filter(
                  call => call.data?.entity_id === entityId
                ).length
                """,
                entity_id,
            )
            control = shadow(page, selector)
            control.evaluate(
                "node => { const disclosure = node.closest('details'); if (disclosure) disclosure.open = true; }"
            )
            control.scroll_into_view_if_needed(timeout=5_000)
            box = control.bounding_box()
            if box is None:
                raise RuntimeError(f"{name} has no hit area")
            page.evaluate(
                """
                selector => {
                  const panel = window.__epPanel;
                  const button = panel.shadowRoot.querySelector(selector);
                  let mutations = 0;
                  const count = records => {
                    mutations += records.filter(
                      record => record.type === 'childList' ||
                        record.type === 'characterData'
                    ).length;
                  };
                  const observer = new MutationObserver(count);
                  observer.observe(button, {
                    childList: true,
                    characterData: true,
                    subtree: true,
                  });
                  window.__epIssue110StopCopyProbe = () => {
                    count(observer.takeRecords());
                    observer.disconnect();
                    return mutations;
                  };
                  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
                  window.__epIssue110Telemetry = (async () => {
                    for (let index = 0; index < 90; index += 1) {
                      window.__epSetEntityByKey(
                        'battery_power', index % 2 ? 925 + index : -1175 - index
                      );
                      await wait(3);
                    }
                  })();
                }
                """,
                selector,
            )
            page.wait_for_timeout(15)
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            page.mouse.move(x, y)
            page.mouse.down()
            page.wait_for_timeout(180)
            mutations = page.evaluate("window.__epIssue110StopCopyProbe()")
            page.mouse.up()
            page.evaluate("window.__epIssue110Telemetry")
            wait_service_count(page, entity_id, before + 1)
            result[f"{name}_click"] = True
            result[f"{name}_copy_stable"] = mutations == 0
            page.wait_for_function(
                "selector => !window.__epPanel.shadowRoot.querySelector(selector)?.disabled",
                arg=selector,
                timeout=10_000,
            )

        stable = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              return {
                renders: window.__epIssue110RenderCount,
                main: window.__epIssue110Identity.main === root.querySelector('main'),
                controls:
                  window.__epIssue110Identity.optimize ===
                    root.querySelector('.ep-optimize-now') &&
                  window.__epIssue110Identity.costfun ===
                    root.querySelector('[data-costfun="cost"]'),
              };
            }
            """
        )
        result["no_full_render"] = stable["renders"] == 0
        result["main_stable"] = stable["main"]
        result["controls_stable"] = stable["controls"]
    except (PlaywrightError, RuntimeError) as err:
        result["error"] = str(err)
    finally:
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              window.__epIssue110StopCopyProbe?.();
              if (window.__epIssue110OriginalRender) {
                panel._render = window.__epIssue110OriginalRender;
              }
              window.__epSetEntity(
                panel._entityId('emhass_cost_function'),
                'Profit',
                {emhass_costfun: 'profit'}
              );
            }
            """
        )
    return result


def exercise_quick_action_state(page: Page, profile: Profile) -> dict[str, object]:
    """Prove split HA state events patch one unambiguous stable selection."""
    enabled = EXPECTED_ENTRYPOINT in {"v045", "v046", "v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "event_ordering": False,
        "pressed_semantics": False,
        "inactive_auto_neutral": False,
        "no_full_render": False,
        "main_stable": False,
        "button_stable": False,
        "delayed_publication": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        page.evaluate(
            """
            () => {
              window.__epSetEntityByKey('control_command', 'battery_charge');
              window.__epSetEntityByKey('automatic_control', 'on');
            }
            """
        )
        page.wait_for_timeout(120)
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              window.__epQuickStateIdentity = {
                main: root.querySelector('main'),
                pause: root.querySelector('[data-action="battery_pause"]'),
              };
              window.__epQuickStateRenderCount = 0;
              window.__epQuickStateOriginalRender = panel._render;
              panel._render = function issue84QuickStateRenderProbe(...args) {
                window.__epQuickStateRenderCount += 1;
                return window.__epQuickStateOriginalRender.apply(this, args);
              };
            }
            """
        )

        ordering = page.evaluate(
            """
            async () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const wait = () => new Promise((resolve) => setTimeout(resolve, 100));
              const snapshot = () => {
                const buttons = [...root.querySelectorAll('.ep-battery-action')];
                const active = buttons.filter((button) => button.classList.contains('active'));
                const pressed = buttons.filter(
                  (button) => button.getAttribute('aria-pressed') === 'true'
                );
                return {
                  active: active.map((button) => button.dataset.action),
                  pressed: pressed.map((button) => button.dataset.action),
                };
              };

              const states = [snapshot()];
              window.__epSetEntityByKey('control_command', 'manual_battery_hold');
              await wait();
              states.push(snapshot());
              window.__epSetEntityByKey('automatic_control', 'off');
              await wait();
              states.push(snapshot());
              window.__epSetEntityByKey('automatic_control', 'on');
              await wait();
              states.push(snapshot());
              window.__epSetEntityByKey('control_command', 'battery_charge');
              await wait();
              window.__epSetEntityByKey('automatic_control', 'off');
              await wait();
              states.push(snapshot());
              window.__epSetEntityByKey('control_command', 'manual_max_charge');
              await wait();
              states.push(snapshot());

              const auto = root.querySelector('[data-action="resume_auto"]');
              const inactive = root.querySelector('[data-action="max_export"]');
              const selected = root.querySelector('[data-action="max_charge"]');
              const autoStyle = getComputedStyle(auto);
              const inactiveStyle = getComputedStyle(inactive);
              const selectedStyle = getComputedStyle(selected);
              return {
                states,
                styles: {
                  autoBackground: autoStyle.backgroundColor,
                  autoImage: autoStyle.backgroundImage,
                  autoBorder: autoStyle.borderColor,
                  inactiveBackground: inactiveStyle.backgroundColor,
                  inactiveBorder: inactiveStyle.borderColor,
                  selectedBackground: selectedStyle.backgroundColor,
                  selectedBorder: selectedStyle.borderColor,
                  selectedImage: selectedStyle.backgroundImage,
                },
              };
            }
            """
        )
        expected = [
            ["resume_auto"],
            ["resume_auto"],
            ["battery_pause"],
            ["resume_auto"],
            [],
            ["max_charge"],
        ]
        result["event_ordering"] = [
            state["active"] for state in ordering["states"]
        ] == expected
        result["pressed_semantics"] = all(
            state["active"] == state["pressed"] for state in ordering["states"]
        )
        styles = ordering["styles"]
        declarative_controls = page.evaluate(
            "Boolean(window.__epPanel.__epControlSurfaceArchitecture)"
        )
        selected_is_distinct = (
            styles["selectedImage"] != "none"
            or styles["selectedBackground"] != styles["autoBackground"]
            or styles["selectedBorder"] != styles["autoBorder"]
        )
        result["inactive_auto_neutral"] = (
            styles["autoImage"] == "none"
            and selected_is_distinct
            and (
                declarative_controls
                or (
                    styles["autoBackground"] == styles["inactiveBackground"]
                    and styles["autoBorder"] == styles["inactiveBorder"]
                )
            )
        )

        page.evaluate(
            """
            () => {
              window.__epSetEntityByKey('control_command', 'battery_charge');
              window.__epSetEntityByKey('automatic_control', 'on');
              window.__epQuickActionPublishDelayMs = 180;
            }
            """
        )
        page.wait_for_timeout(120)
        pause_id = page.evaluate("window.__epPanel._entityId('battery_pause')")
        calls_before = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.data?.entity_id === entityId
            ).length
            """,
            pause_id,
        )
        activate(page, profile, '[data-action="battery_pause"]')
        wait_service_count(page, pause_id, calls_before + 1)
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-action="battery_pause"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )
        stable = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              return {
                renders: window.__epQuickStateRenderCount,
                main: window.__epQuickStateIdentity.main === root.querySelector('main'),
                button: window.__epQuickStateIdentity.pause === root.querySelector(
                  '[data-action="battery_pause"]'
                ),
                selected: root.querySelectorAll('.ep-battery-action.active').length === 1 &&
                  root.querySelector('[data-action="battery_pause"]')?.classList.contains('active'),
                pressed: root.querySelectorAll(
                  '.ep-battery-action[aria-pressed="true"]'
                ).length === 1,
              };
            }
            """
        )
        result["no_full_render"] = stable["renders"] == 0
        result["main_stable"] = stable["main"]
        result["button_stable"] = stable["button"]
        result["delayed_publication"] = stable["selected"] and stable["pressed"]
    except (PlaywrightError, RuntimeError) as err:
        result["error"] = str(err)
    finally:
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              window.__epQuickActionPublishDelayMs = 0;
              if (window.__epQuickStateOriginalRender) {
                panel._render = window.__epQuickStateOriginalRender;
              }
              window.__epSetEntityByKey('control_command', 'battery_charge');
              window.__epSetEntityByKey('automatic_control', 'on');
            }
            """
        )
        page.wait_for_timeout(120)
    return result


def exercise_selector_stability(page: Page, profile: Profile) -> dict[str, object]:
    """Keep EMHASS and manual selectors live without rebuilding the dashboard."""
    enabled = EXPECTED_ENTRYPOINT in {"v045", "v046", "v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "costfun_delayed": False,
        "costfun_external": False,
        "costfun_busy_lock": False,
        "manual_unlocked": False,
        "manual_called": False,
        "no_full_render": False,
        "main_stable": False,
        "controls_stable": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const costfunId = panel._entityId('emhass_cost_function');
              window.__epSetEntity(costfunId, 'Profit', {emhass_costfun: 'profit'});
              window.__epSetEntityByKey('automatic_control', 'on');
            }
            """
        )
        page.wait_for_timeout(120)
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              window.__epSelectorIdentity = {
                main: root.querySelector('main'),
                cost: root.querySelector('[data-costfun="cost"]'),
                manual: root.querySelector('.ep-v021-mode-button[data-mode="8"]'),
              };
              window.__epSelectorRenderCount = 0;
              window.__epSelectorOriginalRender = panel._render;
              panel._render = function issue84SelectorRenderProbe(...args) {
                window.__epSelectorRenderCount += 1;
                return window.__epSelectorOriginalRender.apply(this, args);
              };
              window.__epCostfunPublishDelayMs = 180;
            }
            """
        )

        costfun_id = page.evaluate(
            "window.__epPanel._entityId('emhass_cost_function')"
        )
        costfun_before = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.data?.entity_id === entityId
            ).length
            """,
            costfun_id,
        )
        activate(page, profile, '[data-costfun="cost"]')
        wait_service_count(page, costfun_id, costfun_before + 1)
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-costfun="cost"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )
        result["costfun_delayed"] = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              return root.querySelectorAll('.ep-v016-costfun-button.active').length === 1 &&
                root.querySelectorAll(
                  '.ep-v016-costfun-button[aria-pressed="true"]'
                ).length === 1;
            }
            """
        )

        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              window.__epSetEntity(
                panel._entityId('emhass_cost_function'),
                'Self-consumption',
                {emhass_costfun: 'self-consumption'}
              );
            }
            """
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-costfun="self-consumption"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )
        result["costfun_external"] = True

        page.evaluate(
            """
            () => {
              window.__epCostfunPublishDelayMs = 0;
              window.__epCostfunServiceDelayMs = 500;
            }
            """
        )
        costfun_busy_before = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.data?.entity_id === entityId
            ).length
            """,
            costfun_id,
        )
        activate(page, profile, '[data-costfun="profit"]')
        wait_service_count(page, costfun_id, costfun_busy_before + 1)
        page.evaluate(
            "window.__epSetEntityByKey('battery_power', 1840)"
        )
        page.wait_for_timeout(120)
        busy_state = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const wrap = panel.shadowRoot.querySelector('.ep-v016-costfun');
              const buttons = [...wrap.querySelectorAll('.ep-v016-costfun-button')];
              return {
                flag: panel.__epV016CostfunBusy === 'profit',
                aria: wrap.getAttribute('aria-busy') === 'true',
                disabled: buttons.every((button) => button.disabled),
                pending: wrap.querySelector('[data-costfun="profit"]')?.textContent ===
                  'Applying…',
              };
            }
            """
        )
        busy_button = shadow(page, '[data-costfun="profit"]')
        busy_button.evaluate(
            "node => { const disclosure = node.closest('details'); if (disclosure) disclosure.open = true; }"
        )
        busy_button.scroll_into_view_if_needed(timeout=5_000)
        busy_box = busy_button.bounding_box()
        if busy_box is None:
            raise RuntimeError("Busy EMHASS strategy has no hit area")
        busy_x = busy_box["x"] + busy_box["width"] / 2
        busy_y = busy_box["y"] + busy_box["height"] / 2
        if profile.touch:
            page.touchscreen.tap(busy_x, busy_y)
        else:
            page.mouse.click(busy_x, busy_y)
        page.wait_for_timeout(100)
        busy_calls = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.data?.entity_id === entityId
            ).length
            """,
            costfun_id,
        )
        result["costfun_busy_lock"] = (
            all(busy_state.values())
            and busy_calls == costfun_busy_before + 1
        )
        page.wait_for_function(
            "() => !window.__epPanel.__epV016CostfunBusy",
            timeout=10_000,
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-costfun="profit"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )

        page.evaluate("window.__epSetEntityByKey('automatic_control', 'off')")
        page.wait_for_function(
            """
            () => !window.__epPanel.shadowRoot.querySelector(
              '.ep-v021-mode-button[data-mode="8"]'
            )?.disabled
            """,
            timeout=10_000,
        )
        result["manual_unlocked"] = True
        manual_id = page.evaluate("window.__epPanel._entityId('manual_mode')")
        manual_before = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.data?.entity_id === entityId
            ).length
            """,
            manual_id,
        )
        activate(page, profile, '.ep-v021-mode-button[data-mode="8"]')
        wait_service_count(page, manual_id, manual_before + 1)
        page.wait_for_function(
            "() => !window.__epPanel.__epV021ManualBusy",
            timeout=10_000,
        )
        result["manual_called"] = True

        stable = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              return {
                renders: window.__epSelectorRenderCount,
                main: window.__epSelectorIdentity.main === root.querySelector('main'),
                cost: window.__epSelectorIdentity.cost === root.querySelector(
                  '[data-costfun="cost"]'
                ),
                manual: window.__epSelectorIdentity.manual === root.querySelector(
                  '.ep-v021-mode-button[data-mode="8"]'
                ),
              };
            }
            """
        )
        result["no_full_render"] = stable["renders"] == 0
        result["main_stable"] = stable["main"]
        result["controls_stable"] = stable["cost"] and stable["manual"]
    except (PlaywrightError, RuntimeError) as err:
        result["error"] = str(err)
    finally:
        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              window.__epCostfunPublishDelayMs = 0;
              window.__epCostfunServiceDelayMs = 0;
              if (window.__epSelectorOriginalRender) {
                panel._render = window.__epSelectorOriginalRender;
              }
              window.__epSetEntity(
                panel._entityId('emhass_cost_function'),
                'Profit',
                {emhass_costfun: 'profit'}
              );
              window.__epSetEntityByKey('automatic_control', 'on');
            }
            """
        )
        page.wait_for_timeout(120)
    return result


def exercise_touch_controls(page: Page, profile: Profile) -> dict[str, object]:
    """Exercise repeated real taps and verify semantic, visual and action state."""
    enabled = profile.touch and EXPECTED_ENTRYPOINT in {"v043", "v044", "v045", "v046", "v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}
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
                  const pressed = root.querySelectorAll(
                    '.ep-battery-action[aria-pressed="true"]'
                  );
                  return active.length === 1 && pressed.length === 1 &&
                    active[0].dataset.action === key && pressed[0].dataset.action === key;
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
                      const pressed = [...window.__epPanel.shadowRoot.querySelectorAll(
                        '.ep-battery-action[aria-pressed="true"]'
                      )];
                      return {
                        active: active.length,
                        pressed: pressed.length,
                        key: active[0]?.dataset.action || null,
                        pressedKey: pressed[0]?.dataset.action || null,
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
                snapshot["active"] == 1
                and snapshot["pressed"] == 1
                and snapshot["key"] == key
                and snapshot["pressedKey"] == key
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
    enabled = EXPECTED_ENTRYPOINT in {"v044", "v045", "v046", "v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "single_call": False,
        "no_full_render": False,
        "main_stable": False,
        "optimize_stable": False,
        "layout_stable": False,
        "automatic_stable": False,
        "strategy_stable": False,
        "scroll_anchor_stable": False,
        "button_position_stable": False,
        "floating": False,
        "viewport_reachable": False,
        "safe_edge_spacing": False,
        "touch_target": False,
        "outside_optional_card": False,
        "visible_with_card_hidden": False,
        "footer_clear": False,
        "scroll_working": False,
        "scroll_probe": {},
        "button_idle": False,
        "marker": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        page.evaluate(
            """
            () => {
              const scroller = window.__epScroller;
              const maximum = scroller.scrollHeight - scroller.clientHeight;
              scroller.scrollTop = maximum;
            }
            """
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
                buttonLeft: rect?.left ?? null,
                buttonHeight: rect?.height ?? 0,
                buttonWidth: rect?.width ?? 0,
                position: optimize ? getComputedStyle(optimize).position : "",
                outsideOptionalCard: optimize?.parentElement === root.querySelector("main"),
                viewportReachable: Boolean(
                  rect && rect.top >= 0 && rect.left >= 0 &&
                  rect.bottom <= innerHeight && rect.right <= innerWidth
                ),
                safeEdgeSpacing: Boolean(
                  rect && rect.left >= 10 && rect.top >= 10 &&
                  rect.right <= innerWidth - 10 && rect.bottom <= innerHeight - 10
                ),
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
              const distance = Math.max(320, Math.round(scroller.clientHeight * 0.45));
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
                scrollAnchorDelta:
                  (maximum - afterOptimize) - initial.bottomDistance,
                scrollTopDelta: afterOptimize - initial.scrollTop,
                buttonTopDelta:
                  rect && initial.buttonTop !== null ? rect.top - initial.buttonTop : null,
                buttonLeftDelta:
                  rect && initial.buttonLeft !== null ? rect.left - initial.buttonLeft : null,
                buttonBusy: optimize?.getAttribute('aria-busy'),
                buttonDisabled: Boolean(optimize?.disabled),
                marker: optimize?.dataset?.epV044StableOptimize || '',
              };
              scroller.scrollTop = 0;
              await new Promise((resolve) => setTimeout(resolve, 180));
              const probeStart = scroller.scrollTop;
              const target = Math.min(maximum, probeStart + distance);
              const probeDistance = Math.abs(target - probeStart);
              scroller.scrollTop = target;
              await new Promise((resolve) => setTimeout(resolve, 180));
              const scrolledRect = optimize?.getBoundingClientRect();
              const emhassCard = root.querySelector('[data-ep-card="emhass"]');
              const cardHiddenBefore = Boolean(emhassCard?.hidden);
              if (emhassCard) emhassCard.hidden = true;
              const hiddenRect = optimize?.getBoundingClientRect();
              const visibleWithCardHidden = Boolean(
                optimize && getComputedStyle(optimize).display !== "none" &&
                getComputedStyle(optimize).visibility !== "hidden" &&
                hiddenRect && hiddenRect.width > 0 && hiddenRect.height > 0
              );
              if (emhassCard) emhassCard.hidden = cardHiddenBefore;
              const scrollAfterProbe = scroller.scrollTop;
              scroller.scrollTop = maximum;
              await new Promise((resolve) => setTimeout(resolve, 180));
              const footerRect = root.querySelector("footer")?.getBoundingClientRect();
              const bottomRect = optimize?.getBoundingClientRect();
              const footerClear = Boolean(
                footerRect && bottomRect && footerRect.bottom <= bottomRect.top - 8
              );
              scroller.scrollTop = target;
              return {
                ...beforeProbe,
                probeDistance,
                target,
                scrollAfterProbe,
                scrolledButtonTop: scrolledRect?.top ?? null,
                scrolledButtonLeft: scrolledRect?.left ?? null,
                visibleWithCardHidden,
                footerClear,
              };
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
                "scroll_anchor_stable": abs(measured["scrollAnchorDelta"]) <= 5,
                "button_position_stable": (
                    measured["buttonTopDelta"] is not None
                    and measured["buttonLeftDelta"] is not None
                    and measured["scrolledButtonTop"] is not None
                    and measured["scrolledButtonLeft"] is not None
                    and abs(measured["buttonTopDelta"]) <= 2
                    and abs(measured["buttonLeftDelta"]) <= 2
                    and abs(measured["scrolledButtonTop"] - initial["buttonTop"]) <= 2
                    and abs(measured["scrolledButtonLeft"] - initial["buttonLeft"]) <= 2
                ),
                "floating": initial["position"] == "fixed",
                "viewport_reachable": initial["viewportReachable"],
                "safe_edge_spacing": initial["safeEdgeSpacing"],
                "touch_target": (
                    initial["buttonHeight"] >= 44 and initial["buttonWidth"] >= 44
                ),
                "outside_optional_card": initial["outsideOptionalCard"],
                "visible_with_card_hidden": measured["visibleWithCardHidden"],
                "footer_clear": measured["footerClear"],
                "scroll_working": (
                    measured["probeDistance"] >= 200
                    and abs(measured["scrollAfterProbe"] - measured["target"]) <= 5
                ),
                "scroll_probe": {
                    "distance": measured["probeDistance"],
                    "target": measured["target"],
                    "actual": measured["scrollAfterProbe"],
                },
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


def exercise_chart_size_press(page: Page, profile: Profile) -> dict[str, object]:
    """Refresh the plan card during one physical S/M/L press."""
    enabled = EXPECTED_ENTRYPOINT in {"v047", "v051", "v100", "v101", "v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "refresh_during_press": False,
        "click_delivered": False,
        "size_selected": False,
        "preference_saved": False,
        "single_card": False,
        "main_stable": False,
        "card_stable": False,
        "header_stable": False,
        "button_stable": False,
        "window_bar_present": False,
        "window_bar_stable": False,
        "restored_normal": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.__epV027BatteryPlanData &&
              !window.__epPanel.__epV027BatteryPlanPromise &&
              window.__epPanel.shadowRoot.querySelector('[data-chart-size="compact"]')
            )
            """,
            timeout=15_000,
        )
        button = shadow(page, '[data-chart-size="compact"]')
        button.scroll_into_view_if_needed(timeout=5_000)
        box = button.bounding_box()
        if box is None:
            raise RuntimeError("Compact chart-size button has no hit area")

        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const card = root.querySelector('.ep-v027-battery-plan-card');
              const button = root.querySelector('[data-chart-size="compact"]');
              window.__epIssue97Identity = {
                main: root.querySelector('main'),
                card,
                header: card.querySelector(':scope > .ep-v027-head'),
                button,
                windowBar: card.querySelector(':scope > .ep-v031-card-windowbar'),
                renderKey: card.dataset.epRenderKey || '',
                clicks: 0,
              };
              button.addEventListener('click', () => {
                window.__epIssue97Identity.clicks += 1;
              });
              root.addEventListener('pointerdown', () => {
                panel.__epV027BatteryPlanData = {
                  ...panel.__epV027BatteryPlanData,
                  at: panel.__epV027BatteryPlanData.at + 1,
                };
                panel.__epV041RefreshBatteryPlan();
              }, {capture: true, once: true});
            }
            """
        )

        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        if profile.touch:
            page.touchscreen.tap(x, y)
        else:
            page.mouse.move(x, y)
            page.mouse.down()
            page.wait_for_timeout(80)
            page.mouse.up()
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v027-battery-plan-card'
            )?.classList.contains('size-compact')
            """,
            timeout=10_000,
        )
        result.update(
            page.evaluate(
                """
                () => {
                  const root = window.__epPanel.shadowRoot;
                  const card = root.querySelector('.ep-v027-battery-plan-card');
                  const selected = card.querySelector(
                    '[data-chart-size="compact"]'
                  );
                  let stored = null;
                  try {
                    stored = JSON.parse(
                      localStorage.getItem('gw_energypilot_dashboard_v008') || '{}'
                    )?.sizes?.['battery-price'] || null;
                  } catch (_err) {
                    stored = null;
                  }
                  return {
                    refresh_during_press:
                      card.dataset.epRenderKey !== window.__epIssue97Identity.renderKey,
                    click_delivered: window.__epIssue97Identity.clicks === 1,
                    size_selected:
                      card.classList.contains('size-compact') &&
                      selected?.getAttribute('aria-pressed') === 'true',
                    preference_saved: stored === 'compact',
                    single_card:
                      root.querySelectorAll('.ep-v027-battery-plan-card').length === 1,
                    main_stable:
                      window.__epIssue97Identity.main === root.querySelector('main'),
                    card_stable: window.__epIssue97Identity.card === card,
                    header_stable:
                      window.__epIssue97Identity.header ===
                        card.querySelector(':scope > .ep-v027-head'),
                    button_stable:
                      window.__epIssue97Identity.button === selected &&
                      selected?.isConnected === true,
                    window_bar_present: Boolean(window.__epIssue97Identity.windowBar),
                    window_bar_stable:
                      window.__epIssue97Identity.windowBar ===
                        card.querySelector(':scope > .ep-v031-card-windowbar'),
                  };
                }
                """
            )
        )
        activate(page, profile, '[data-chart-size="normal"]')
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v027-battery-plan-card'
            )?.classList.contains('size-normal')
            """,
            timeout=10_000,
        )
        result["restored_normal"] = True
    except (PlaywrightError, RuntimeError) as err:
        result["error"] = str(err)
    return result


def exercise_chart_range_press(page: Page, profile: Profile) -> dict[str, object]:
    """Switch 12/24/36-hour views without reloading Recorder or replacing controls."""
    enabled = EXPECTED_ENTRYPOINT in {"v050", "v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "refresh_during_press": False,
        "click_delivered": False,
        "range12_selected": False,
        "rolling_window": False,
        "preference_saved": False,
        "no_recorder_reload": False,
        "range36_selected": False,
        "fixed_36_window": False,
        "restored_24": False,
        "single_card": False,
        "main_stable": False,
        "card_stable": False,
        "header_stable": False,
        "button_stable": False,
        "window_bar_stable": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.__epV027BatteryPlanData?.chartTime &&
              !window.__epPanel.__epV027BatteryPlanPromise &&
              Number(window.__epPanel.__epV027BatteryPlanData?.payload?.plan_revision) ===
                Number(window.__epHass.states[
                  window.__epPanel._entityId('optimize_now')
                ]?.attributes?.plan_revision) &&
              window.__epPanel.shadowRoot.querySelector('[data-chart-range="12h"]')
            )
            """,
            timeout=15_000,
        )
        button = shadow(page, '[data-chart-range="12h"]')
        button.scroll_into_view_if_needed(timeout=5_000)
        box = button.bounding_box()
        if box is None:
            raise RuntimeError("12-hour range button has no hit area")

        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const card = root.querySelector('.ep-v027-battery-plan-card');
              const button = root.querySelector('[data-chart-range="12h"]');
              window.__epIssue102Identity = {
                main: root.querySelector('main'),
                card,
                header: card.querySelector(':scope > .ep-v027-head'),
                button,
                windowBar: card.querySelector(':scope > .ep-v031-card-windowbar'),
                renderKey: card.dataset.epRenderKey || '',
                recorderCalls: window.__epWsCalls.filter(
                  call => call.type === 'recorder/statistics_during_period' ||
                    call.type === 'history/history_during_period'
                ).length,
                clicks: 0,
              };
              button.addEventListener('click', () => {
                window.__epIssue102Identity.clicks += 1;
              });
              root.addEventListener('pointerdown', () => {
                panel.__epV027BatteryPlanData = {
                  ...panel.__epV027BatteryPlanData,
                  at: panel.__epV027BatteryPlanData.at + 1,
                };
                panel.__epV041RefreshBatteryPlan();
              }, {capture: true, once: true});
            }
            """
        )

        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        if profile.touch:
            page.touchscreen.tap(x, y)
        else:
            page.mouse.move(x, y)
            page.mouse.down()
            page.wait_for_timeout(80)
            page.mouse.up()
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-chart-range="12h"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )
        first = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const card = root.querySelector('.ep-v027-battery-plan-card');
              const button = root.querySelector('[data-chart-range="12h"]');
              const chartTime = window.__epPanel.__epV027BatteryPlanData.chartTime;
              const rolling = chartTime.windows['12h'];
              let stored = null;
              try {
                stored = JSON.parse(
                  localStorage.getItem('gw_energypilot_dashboard_v008') || '{}'
                )?.ranges?.['battery-price'] || null;
              } catch (_err) {
                stored = null;
              }
              return {
                refreshDuringPress:
                  card.dataset.epRenderKey !== window.__epIssue102Identity.renderKey,
                clickDelivered: window.__epIssue102Identity.clicks === 1,
                selected: button?.getAttribute('aria-pressed') === 'true',
                rollingWindow:
                  rolling.endMs - rolling.startMs === 12 * 60 * 60 * 1000 &&
                  Math.abs((rolling.startMs + rolling.endMs) / 2 - chartTime.nowMs) < 2,
                stored,
              };
            }
            """
        )
        result["refresh_during_press"] = first["refreshDuringPress"]
        result["click_delivered"] = first["clickDelivered"]
        result["range12_selected"] = first["selected"]
        result["rolling_window"] = first["rollingWindow"]
        result["preference_saved"] = first["stored"] == "12h"

        activate(page, profile, '[data-chart-range="36h"]')
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-chart-range="36h"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )
        second = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const card = root.querySelector('.ep-v027-battery-plan-card');
              const chartTime = window.__epPanel.__epV027BatteryPlanData.chartTime;
              const fixed = chartTime.windows['36h'];
              const recorderCalls = window.__epWsCalls.filter(
                call => call.type === 'recorder/statistics_during_period' ||
                  call.type === 'history/history_during_period'
              ).length;
              return {
                range36Selected: card.querySelector(
                  '[data-chart-range="36h"]'
                )?.getAttribute('aria-pressed') === 'true',
                fixed36:
                  fixed.startMs === chartTime.dayStartMs &&
                  fixed.endMs === chartTime.maxEndMs,
                noRecorderReload:
                  recorderCalls === window.__epIssue102Identity.recorderCalls,
                singleCard:
                  root.querySelectorAll('.ep-v027-battery-plan-card').length === 1,
                mainStable:
                  window.__epIssue102Identity.main === root.querySelector('main'),
                cardStable: window.__epIssue102Identity.card === card,
                headerStable:
                  window.__epIssue102Identity.header ===
                    card.querySelector(':scope > .ep-v027-head'),
                buttonStable:
                  window.__epIssue102Identity.button ===
                    card.querySelector('[data-chart-range="12h"]') &&
                  window.__epIssue102Identity.button.isConnected === true,
                windowBarStable:
                  window.__epIssue102Identity.windowBar ===
                    card.querySelector(':scope > .ep-v031-card-windowbar'),
              };
            }
            """
        )
        result["range36_selected"] = second["range36Selected"]
        result["fixed_36_window"] = second["fixed36"]
        result["no_recorder_reload"] = second["noRecorderReload"]
        result["single_card"] = second["singleCard"]
        result["main_stable"] = second["mainStable"]
        result["card_stable"] = second["cardStable"]
        result["header_stable"] = second["headerStable"]
        result["button_stable"] = second["buttonStable"]
        result["window_bar_stable"] = second["windowBarStable"]

        activate(page, profile, '[data-chart-range="24h"]')
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-chart-range="24h"]'
            )?.getAttribute('aria-pressed') === 'true'
            """,
            timeout=10_000,
        )
        result["restored_24"] = True
    except (PlaywrightError, RuntimeError) as err:
        result["error"] = str(err)
    return result


def exercise_plan_refresh(page: Page) -> dict[str, object]:
    result: dict[str, object] = {
        "ready": False,
        "data_changed": False,
        "card_stable": False,
        "main_stable": False,
        "layout_control_stable": False,
        "auto_control_stable": False,
        "optimize_control_stable": False,
        "costfun_control_stable": False,
        "max_export_control_stable": False,
        "strategy_control_stable": False,
        "actual_soc_visible": False,
        "forecast_soc_visible": False,
        "soc_axis_visible": False,
        "soc_values_valid": False,
        "soc_targets_interval_end": False,
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
                  const data = window.__epPanel.__epV027BatteryPlanData;
                  const sourcePoint = data?.payload?.battery_soc_plan?.points?.find(
                    point => point.value_pct >= 0 && point.value_pct <= 100
                  );
                  const normalizedPoint = data?.socPlanPoints?.find(
                    point => point.t === Date.parse(sourcePoint?.target_at)
                  );
                  return {
                    data_changed:
                      window.__epPanel.__epV027BatteryPlanData?.payload?.plan_revision !== previousRevision,
                    card_stable:
                      window.__epPlanIdentity.card === root.querySelector('.ep-v027-battery-plan-card'),
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
                    actual_soc_visible: Boolean(
                      root.querySelector('.ep-v027-battery-plan-card [data-series="actual-soc"]')
                    ),
                    forecast_soc_visible: Boolean(
                      root.querySelector('.ep-v027-battery-plan-card [data-series="forecast-soc"]')
                    ),
                    soc_axis_visible: Array.from(
                      root.querySelectorAll('.ep-v027-battery-plan-card svg text')
                    ).some(node => node.textContent?.trim() === 'SOC (%)'),
                    soc_values_valid: Boolean(
                      data?.actualSocRows?.length &&
                      data?.socPlanPoints?.length &&
                      data.actualSocRows.every(
                        point => point.pct >= 0 && point.pct <= 100
                      ) &&
                      data.socPlanPoints.every(
                        point => point.pct >= 0 && point.pct <= 100
                      )
                    ),
                    soc_targets_interval_end: Boolean(
                      sourcePoint && normalizedPoint &&
                      data.payload.battery_soc_plan.timestamp_semantics === 'interval_end' &&
                      Date.parse(sourcePoint.target_at) ===
                        Date.parse(sourcePoint.start) +
                          data.payload.battery_soc_plan.step_seconds * 1000
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
        "flow_localized": False,
        "help_localized": False,
        "manual_summary_localized": False,
        "setpoint_update_localized": False,
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
        result["manual_summary_localized"] = page.evaluate(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v021-manual-pad [data-manual-note]'
            )?.textContent.includes('Automatische regeling bestuurt de omvormer.')
            """
        )
        result["setpoint_update_localized"] = page.evaluate(
            """
            () => Array.from(window.__epPanel.shadowRoot.querySelectorAll(
              '.panel-card.controller .metric'
            )).find(metric => metric.querySelector('.metric-label')?.textContent.trim() === 'EMS-setpoint')
              ?.querySelector('.metric-sub')?.textContent.trim().startsWith('Laatste update:') === true
            """
        )
        result["help_localized"] = page.evaluate(
            """
            () => {
              const help = window.__epPanel.shadowRoot.querySelector('.ep-v016-help-button');
              return Boolean(
                help?.href.endsWith('/docs/HANDLEIDING_NL.md') &&
                help?.getAttribute('aria-label') === 'Open de GW EnergyPilot-handleiding'
              );
            }
            """
        )
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
                flowLabel:
                  root.querySelector('.ep-link-grid')?.getAttribute('aria-label') || '',
              };
            }
            """
        )
        result["main_stable_during_telemetry"] = telemetry["mainStable"]
        result["flow_localized"] = (
            "Systeem naar net" in telemetry["flowLabel"]
            and "relatieve stroom" in telemetry["flowLabel"]
        )
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
              window.__epPanel.shadowRoot.querySelector('main') !==
                window.__epBeforeNarrowMain &&
              window.__epPanel.shadowRoot.querySelectorAll('[data-ep-card]').length >= 8
            )
            """,
            timeout=10_000,
        )
        wait_render_idle(page)
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
        "split_nodes": False,
        "routes_match": False,
        "telemetry_main_stable": False,
        "external_value_matches": False,
        "flow_values_match": False,
        "flow_nodes_stable": False,
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
              const expectedInternal = panel._formatPower(
                Number(aggregate.attributes.internal_power_w)
              );
              const expectedExternal = panel._formatPower(
                Number(aggregate.attributes.external_power_w)
              );
              const main = root.querySelector('main');
              window.__epPvTelemetryMain = main;
              const scroller = window.__epScroller;
              scroller.scrollTop = Math.max(
                0,
                Math.round((scroller.scrollHeight - scroller.clientHeight) * 0.36)
              );
              window.__epPvScrollBefore = scroller.scrollTop;
              const group = root.querySelector('.ep-flow-pv-group');
              const internalNode = group?.querySelector('.ep-flow-pv-internal');
              const externalNode = group?.querySelector('.ep-flow-pv-external');
              const internalLink = root.querySelector('.ep-link-pv-internal');
              const externalLink = root.querySelector('.ep-link-pv-external');
              const batteryLink = root.querySelector('.ep-link-battery');
              const hub = root.querySelector('.ep-flow-hub');
              const internalRect = internalLink?.getBoundingClientRect();
              const externalRect = externalLink?.getBoundingClientRect();
              const batteryRect = batteryLink?.getBoundingClientRect();
              const hubRect = hub?.getBoundingClientRect();
              window.__epPvFlowIdentity = {
                group,
                internalNode,
                externalNode,
                internalLink,
                externalLink,
              };
              return {
                topologyRendered: window.__epPvBeforeTopologyMain !== main,
                sourceCount: root.querySelectorAll(
                  '.energy-card.solar [data-pv-source-index]'
                ).length,
                totalMatches:
                  root.querySelector('.energy-card.solar .hero-value')?.textContent === expected,
                flowMatches:
                  group?.querySelector('.ep-flow-pv-total-value')?.textContent === expected,
                splitNodes: Boolean(
                  group?.dataset.epPvFlowTopology === 'both' &&
                  internalNode && !internalNode.hidden &&
                  externalNode && !externalNode.hidden &&
                  internalNode.querySelector('.ep-flow-node-value')?.textContent === expectedInternal &&
                  externalNode.querySelector('.ep-flow-node-value')?.textContent === expectedExternal
                ),
                routesMatch: Boolean(
                  internalRect && externalRect && batteryRect && hubRect &&
                  internalLink.dataset.epPvRoute === 'internal' &&
                  externalLink.dataset.epPvRoute === 'external' &&
                  internalRect.top > externalRect.top &&
                  Math.abs(internalRect.right - (batteryRect.left + batteryRect.width / 2)) <= 4 &&
                  externalRect.right >= hubRect.left - 18 &&
                  externalRect.right <= hubRect.right
                ),
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
              const group = root.querySelector('.ep-flow-pv-group');
              const internalNode = group?.querySelector('.ep-flow-pv-internal');
              const externalNode = group?.querySelector('.ep-flow-pv-external');
              const aggregate = window.__epHass.states[
                panel._entityId('pv_generation_power')
              ];
              return {
                mainStable: window.__epPvTelemetryMain === root.querySelector('main'),
                externalMatches: external?.textContent === panel._formatPower(1700),
                flowValuesMatch: Boolean(
                  group?.querySelector('.ep-flow-pv-total-value')?.textContent ===
                    panel._formatPower(Number(aggregate.state)) &&
                  internalNode?.querySelector('.ep-flow-node-value')?.textContent ===
                    panel._formatPower(Number(aggregate.attributes.internal_power_w)) &&
                  externalNode?.querySelector('.ep-flow-node-value')?.textContent ===
                    panel._formatPower(1700)
                ),
                flowNodesStable: Boolean(
                  window.__epPvFlowIdentity.group === group &&
                  window.__epPvFlowIdentity.internalNode === internalNode &&
                  window.__epPvFlowIdentity.externalNode === externalNode &&
                  window.__epPvFlowIdentity.internalLink === root.querySelector('.ep-link-pv-internal') &&
                  window.__epPvFlowIdentity.externalLink === root.querySelector('.ep-link-pv-external')
                ),
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
                "split_nodes": topology["splitNodes"],
                "routes_match": topology["routesMatch"],
                "telemetry_main_stable": telemetry["mainStable"],
                "external_value_matches": telemetry["externalMatches"],
                "flow_values_match": telemetry["flowValuesMatch"],
                "flow_nodes_stable": telemetry["flowNodesStable"],
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
        "external_checked": False,
        "external_fields": 0,
        "fields_grouped": False,
        "disabled_when_off": False,
        "enabled_when_on": False,
        "value_preserved": False,
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
            async () => {
              const root = window.__epPanel.shadowRoot;
              const form = root.querySelector('.ep-v016-form[data-section="pv"]');
              const externalToggle = form?.querySelector(
                '[data-setting-key="enable_external_pv"]'
              );
              const fields = [...(form?.querySelectorAll(
                '[data-setting-key^="external_pv_entity_"]'
              ) || [])];
              const group = form?.querySelector('[data-pv-external-group]');
              const initialValue = fields[0]?.value;
              externalToggle.click();
              await new Promise((resolve) => setTimeout(resolve, 20));
              const disabledWhenOff = fields.every((field) => field.disabled) &&
                group?.classList.contains('is-disabled');
              externalToggle.click();
              await new Promise((resolve) => setTimeout(resolve, 20));
              const enabledWhenOn = fields.every((field) => !field.disabled) &&
                group?.classList.contains('is-enabled');
              return {
                internalChecked: Boolean(
                  form?.querySelector('[data-setting-key="enable_internal_pv"]')?.checked
                ),
                externalChecked: Boolean(externalToggle?.checked),
                externalFields: fields.length,
                fieldsGrouped: Boolean(group) && fields.every((field) => group.contains(field)),
                disabledWhenOff,
                enabledWhenOn,
                valuePreserved: fields[0]?.value === initialValue,
                entitySearchContainsSource: [...(form?.querySelectorAll('datalist option') || [])]
                  .some((option) => option.value === 'sensor.external_roof_pv'),
              };
            }
            """
        )
        result["internal_checked"] = state["internalChecked"]
        result["external_checked"] = state["externalChecked"]
        result["external_fields"] = state["externalFields"]
        result["fields_grouped"] = state["fieldsGrouped"]
        result["disabled_when_off"] = state["disabledWhenOff"]
        result["enabled_when_on"] = state["enabledWhenOn"]
        result["value_preserved"] = state["valuePreserved"]
        result["entity_search_contains_source"] = state["entitySearchContainsSource"]
        activate(page, profile, '[data-discard]')
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


def exercise_deadband_settings(page: Page, profile: Profile) -> dict[str, object]:
    """Verify the beta.2 EP deadband panel, validation and responsive fit."""
    enabled = EXPECTED_ENTRYPOINT in {"v101", "v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "inputs_present": False,
        "defaults_correct": False,
        "zero_centered": False,
        "directions_present": False,
        "modes_correct": False,
        "invalid_blocked": False,
        "valid_restored": False,
        "submitted_both": False,
        "responsive_fit": False,
        "closed": False,
        "error": None,
    }
    if not enabled:
        return result
    try:
        activate(page, profile, ".ep-v016-settings-button")
        page.wait_for_selector(
            'gw-energypilot-panel >> .ep-v016-form[data-section="energypilot"]',
            timeout=10_000,
        )
        state = page.evaluate(
            """
            async () => {
              const root = window.__epPanel.shadowRoot;
              const form = root.querySelector('.ep-v016-form[data-section="energypilot"]');
              const group = form?.querySelector('.ep-v016-deadband-group');
              const hold = form?.querySelector('[data-setting-key="deadband"]');
              const automatic = form?.querySelector(
                '[data-setting-key="goodwe_auto_deadband"]'
              );
              const zero = form?.querySelector('.ep-v016-deadband-zero');
              const windowBar = form?.querySelector('.ep-v016-deadband-window');
              const direction = form?.querySelector('.ep-v016-deadband-direction')
                ?.textContent || '';
              const modes = [...(windowBar?.querySelectorAll('span') || [])]
                .map((item) => item.textContent?.trim());
              const zeroRect = zero?.getBoundingClientRect();
              const windowRect = windowBar?.getBoundingClientRect();
              const defaultsCorrect = hold?.value === '100' && automatic?.value === '1000';

              hold.value = '1000';
              hold.dispatchEvent(new Event('input', { bubbles: true }));
              const invalidBlocked = Boolean(
                !form.querySelector('[data-deadband-validation]')?.hidden &&
                form.querySelector('button[type="submit"]')?.disabled &&
                !hold.checkValidity()
              );

              hold.value = '100';
              hold.dispatchEvent(new Event('input', { bubbles: true }));
              automatic.value = '1000';
              automatic.dispatchEvent(new Event('input', { bubbles: true }));
              const validRestored = Boolean(
                form.querySelector('[data-deadband-validation]')?.hidden &&
                !form.querySelector('button[type="submit"]')?.disabled &&
                hold.checkValidity() && automatic.checkValidity()
              );

              form.dispatchEvent(new Event('submit', {
                bubbles: true, composed: true, cancelable: true,
              }));
              await new Promise((resolve) => setTimeout(resolve, 120));
              const call = [...window.__epWsCalls].reverse().find(
                (item) => item.type === 'gw_energypilot/settings/update' &&
                  item.section === 'energypilot'
              );
              return {
                inputsPresent: Boolean(hold && automatic),
                defaultsCorrect,
                zeroCentered: Boolean(
                  zero?.textContent?.trim() === '0 W' && zeroRect && windowRect &&
                  Math.abs(
                    (zeroRect.left + zeroRect.width / 2) -
                    (windowRect.left + windowRect.width / 2)
                  ) <= 2
                ),
                directionsPresent:
                  direction.includes('Charge') && direction.includes('negative P_batt') &&
                  direction.includes('positive P_batt') && direction.includes('Discharge'),
                modesCorrect: JSON.stringify(modes) === JSON.stringify([
                  'mode 10', 'mode 1', 'mode 8', 'mode 1', 'mode 9'
                ]),
                invalidBlocked,
                validRestored,
                submittedBoth: call?.values?.deadband === 100 &&
                  call?.values?.goodwe_auto_deadband === 1000,
                responsiveFit: Boolean(group) && group.scrollWidth <= group.clientWidth + 1,
              };
            }
            """
        )
        for key, value in state.items():
            result[
                {
                    "inputsPresent": "inputs_present",
                    "defaultsCorrect": "defaults_correct",
                    "zeroCentered": "zero_centered",
                    "directionsPresent": "directions_present",
                    "modesCorrect": "modes_correct",
                    "invalidBlocked": "invalid_blocked",
                    "validRestored": "valid_restored",
                    "submittedBoth": "submitted_both",
                    "responsiveFit": "responsive_fit",
                }[key]
            ] = value
        activate(page, profile, ".ep-v016-back")
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-v016-settings')",
            timeout=10_000,
        )
        result["closed"] = True
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_sems_settings(page: Page, profile: Profile) -> dict[str, object]:
    """Verify the SEMS Beta selector, secret field and local-control boundary."""
    enabled = EXPECTED_ENTRYPOINT in {"v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "tab_present": False,
        "choices_present": False,
        "sems_disabled_in_local_mode": False,
        "sems_enabled_in_cloud_mode": False,
        "local_control_stays_enabled": False,
        "password_protected": False,
        "boundary_copy_present": False,
        "submitted_complete": False,
        "closed": False,
        "error": None,
    }
    if not enabled:
        return result
    try:
        activate(page, profile, ".ep-v016-settings-button")
        page.wait_for_selector(
            'gw-energypilot-panel >> [data-settings-tab="goodwe"]',
            timeout=10_000,
        )
        result["tab_present"] = True
        activate(page, profile, '[data-settings-tab="goodwe"]')
        page.wait_for_selector(
            'gw-energypilot-panel >> .ep-v016-form[data-section="goodwe"]',
            timeout=10_000,
        )
        state = page.evaluate(
            """
            async () => {
              const root = window.__epPanel.shadowRoot;
              const form = root.querySelector('.ep-v016-form[data-section="goodwe"]');
              const source = form?.querySelector('[data-setting-key="telemetry_source"]');
              const username = form?.querySelector('[data-setting-key="sems_username"]');
              const password = form?.querySelector('[data-setting-key="sems_password"]');
              const station = form?.querySelector('[data-setting-key="sems_station_id"]');
              const serial = form?.querySelector('[data-setting-key="sems_inverter_serial"]');
              const cadence = form?.querySelector('[data-setting-key="sems_scan_interval"]');
              const local = ['host', 'port', 'slave'].map((key) =>
                form?.querySelector(`[data-setting-key="${key}"]`)
              );
              const choicesPresent = source?.value === 'modbus' &&
                [...source.options].some((option) => option.value === 'modbus') &&
                [...source.options].some((option) => option.value === 'sems_api');
              const semsDisabledInLocalMode = [username, password, station, serial, cadence]
                .every((input) => input?.disabled === true);
              source.value = 'sems_api';
              source.dispatchEvent(new Event('change', { bubbles: true }));
              const semsEnabledInCloudMode = [username, password, station, serial, cadence]
                .every((input) => input?.disabled === false) && username?.required === true;
              const localControlStaysEnabled = local.every((input) => input?.disabled === false);
              const passwordProtected = password?.type === 'password' &&
                password?.value === '' && password?.autocomplete === 'new-password';
              const boundaryCopyPresent = root.querySelector('.ep-v016-goodwe-note')
                ?.textContent?.includes('Every EMS mode/setpoint command still uses the local Modbus');
              password.value = 'browser-secret';
              form.dispatchEvent(new Event('submit', {
                bubbles: true, composed: true, cancelable: true,
              }));
              await new Promise((resolve) => setTimeout(resolve, 120));
              const call = [...window.__epWsCalls].reverse().find(
                (item) => item.type === 'gw_energypilot/settings/update' &&
                  item.section === 'goodwe'
              );
              return {
                choicesPresent,
                semsDisabledInLocalMode,
                semsEnabledInCloudMode,
                localControlStaysEnabled,
                passwordProtected,
                boundaryCopyPresent,
                submittedComplete: call?.values?.telemetry_source === 'sems_api' &&
                  call?.values?.sems_username === 'visitor@example.com' &&
                  call?.values?.sems_password === 'browser-secret' &&
                  call?.values?.sems_station_id === 'station-1' &&
                  call?.values?.sems_inverter_serial === 'ETA15TEST0001' &&
                  call?.values?.sems_scan_interval === 60 &&
                  call?.values?.host === '192.0.2.10' &&
                  call?.values?.port === 502 && call?.values?.slave === 247,
              };
            }
            """
        )
        result.update(
            {
                "choices_present": state["choicesPresent"],
                "sems_disabled_in_local_mode": state["semsDisabledInLocalMode"],
                "sems_enabled_in_cloud_mode": state["semsEnabledInCloudMode"],
                "local_control_stays_enabled": state["localControlStaysEnabled"],
                "password_protected": state["passwordProtected"],
                "boundary_copy_present": state["boundaryCopyPresent"],
                "submitted_complete": state["submittedComplete"],
            }
        )
        activate(page, profile, ".ep-v016-back")
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-v016-settings')",
            timeout=10_000,
        )
        result["closed"] = True
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_ev_settings(page: Page, profile: Profile) -> dict[str, object]:
    """Verify the EV tab, entity filtering and >16 A acknowledgement path."""
    result: dict[str, object] = {
        "ran": False,
        "tab_present": False,
        "detection_choice_present": False,
        "power_source_exclusive": False,
        "status_source_exclusive": False,
        "detection_submitted": False,
        "profiles_present": False,
        "recommended_window": False,
        "feedback_entity_present": False,
        "manual_grid_current_removed": False,
        "goodwe_source_present": False,
        "charger_entity_present": False,
        "warning_prominent": False,
        "confirmation_sent": False,
        "closed": False,
        "error": None,
    }
    try:
        activate(page, profile, ".ep-v016-settings-button")
        page.wait_for_selector(
            'gw-energypilot-panel >> [data-settings-tab="ev"]', timeout=10_000
        )
        result["tab_present"] = True
        activate(page, profile, '[data-settings-tab="ev"]')
        page.wait_for_selector(
            'gw-energypilot-panel >> .ep-v016-form[data-section="ev"]',
            timeout=10_000,
        )
        page.evaluate("window.confirm = () => true")
        state = page.evaluate(
            """
            async () => {
              const root = window.__epPanel.shadowRoot;
              const form = root.querySelector('.ep-v016-form[data-section="ev"]');
              const detection = form.querySelector('[data-setting-key="ev_detection_method"]');
              const status = form.querySelector('[data-setting-key="ev_mode_entity"]');
              const power = form.querySelector('[data-setting-key="ev_power_entity"]');
              const threshold = form.querySelector('[data-setting-key="ev_deadband"]');
              const profile = form.querySelector('[data-setting-key="grid_connection_profile"]');
              const windowSelect = form.querySelector('[data-setting-key="ev_load_balance_window"]');
              const max = form.querySelector('[data-setting-key="ev_charger_max_current"]');
              const datalistValues = [...form.querySelectorAll('datalist option')]
                .map((option) => option.value);
              const detectionChoicePresent = detection?.value === 'power' &&
                [...detection.options].some((option) => option.value === 'power') &&
                [...detection.options].some((option) => option.value === 'state');
              const powerSourceExclusive = status?.disabled === true &&
                power?.disabled === false && threshold?.disabled === false;
              detection.value = 'state';
              detection.dispatchEvent(new Event('change', { bubbles: true }));
              const statusSourceExclusive = status?.disabled === false &&
                power?.disabled === true && threshold?.disabled === true;
              max.value = '20';
              max.dispatchEvent(new Event('input', { bubbles: true }));
              const warningProminent = root.querySelector('[data-ev-safety-note]')
                ?.classList.contains('danger');
              form.dispatchEvent(new Event('submit', {
                bubbles: true, composed: true, cancelable: true,
              }));
              await new Promise((resolve) => setTimeout(resolve, 100));
              const call = [...window.__epWsCalls].reverse().find(
                (item) => item.type === 'gw_energypilot/settings/update' && item.section === 'ev'
              );
              return {
                detectionChoicePresent,
                powerSourceExclusive,
                statusSourceExclusive,
                profilesPresent: [...profile.options].some((option) => option.value === '3x25') &&
                  [...profile.options].some((option) => option.value === 'custom_1_phase') &&
                  [...profile.options].some((option) => option.value === 'custom_3_phase'),
                recommendedWindow: windowSelect.value === '15',
                feedbackEntityPresent: datalistValues.includes(
                  'sensor.zorro_de_zaptec_laadpaal_toegewezen_laadstroom'
                ),
                manualGridCurrentRemoved: !form.querySelector(
                  '[data-setting-key="ev_grid_current_entity"]'
                ),
                goodweSourcePresent: root.textContent.includes(
                  'Automatic · GoodWe meter L1/L2/L3'
                ),
                chargerEntityPresent: datalistValues.includes('number.zaptec_max_current'),
                warningProminent,
                detectionSubmitted: call?.values?.ev_detection_method === 'state' &&
                  call?.values?.ev_mode_entity === 'binary_sensor.tesla_wall_connector_opladen' &&
                  call?.values?.ev_power_entity === 'sensor.zaptec_charge_power' &&
                  call?.values?.ev_deadband === 500,
                confirmationSent: call?.values?.ev_charger_max_current === 20 &&
                  call?.values?._confirm_high_current === true,
              };
            }
            """
        )
        result.update({
            "detection_choice_present": state["detectionChoicePresent"],
            "power_source_exclusive": state["powerSourceExclusive"],
            "status_source_exclusive": state["statusSourceExclusive"],
            "detection_submitted": state["detectionSubmitted"],
            "profiles_present": state["profilesPresent"],
            "recommended_window": state["recommendedWindow"],
            "feedback_entity_present": state["feedbackEntityPresent"],
            "manual_grid_current_removed": state["manualGridCurrentRemoved"],
            "goodwe_source_present": state["goodweSourcePresent"],
            "charger_entity_present": state["chargerEntityPresent"],
            "warning_prominent": state["warningProminent"],
            "confirmation_sent": state["confirmationSent"],
        })
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


def exercise_execution_history(page: Page, profile: Profile) -> dict[str, object]:
    result: dict[str, object] = {
        "ran": False,
        "single_card": False,
        "compact_rows": False,
        "future_rows": False,
        "wanted_soc_history": False,
        "source_bars": False,
        "ev_charge_underlay": False,
        "ev_hold_underlay": False,
        "modal_open": False,
        "modal_rows": False,
        "modal_no_filter": False,
        "card_stable": False,
        "main_stable": False,
        "modal_closed": False,
        "error": None,
    }
    if EXPECTED_ENTRYPOINT not in {"v051", "v100", "v101", "v110", "v130"}:
        return result
    try:
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.__epV027BatteryPlanData?.payload?.execution &&
              !window.__epPanel.__epV027BatteryPlanPromise &&
              window.__epPanel.shadowRoot.querySelector('.ep-v051-history-card')
            )
            """,
            timeout=15_000,
        )
        initial = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              window.__epV051HistoryIdentity = {
                main: root.querySelector('main'),
                card: root.querySelector('.ep-v051-history-card'),
              };
              return {
                cards: root.querySelectorAll('.ep-v051-history-card').length,
                rows: root.querySelectorAll('.ep-v051-history-card tbody tr').length,
                futureRows: root.querySelectorAll(
                  '.ep-v051-history-card tbody tr[data-kind="projection"]'
                ).length,
                wantedHistory: Number(
                  root.querySelector('[data-series="forecast-soc"]')?.dataset.historyPoints || 0
                ),
                evChargeUnderlay: Boolean(root.querySelector(
                  '[data-series="ev-protection"][data-ev-kind="battery_charge_allowed"]'
                )),
                evHoldUnderlay: Boolean(root.querySelector(
                  '[data-series="ev-protection"][data-ev-kind="discharge_blocked"]'
                )),
              };
            }
            """
        )
        result.update(
            {
                "single_card": initial["cards"] == 1,
                "compact_rows": initial["rows"] >= 4,
                "future_rows": initial["futureRows"] >= 1,
                "wanted_soc_history": initial["wantedHistory"] >= 1,
                "ev_charge_underlay": initial["evChargeUnderlay"],
                "ev_hold_underlay": initial["evHoldUnderlay"],
            }
        )

        activate(page, profile, '.ep-v027-battery-plan-card [data-chart-size="large"]')
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.shadowRoot.querySelector(
                '.ep-v027-battery-plan-card [data-source-series]'
              )
            )
            """,
            timeout=10_000,
        )
        result["source_bars"] = True
        activate(page, profile, '.ep-v027-battery-plan-card [data-chart-size="normal"]')

        activate(page, profile, '.ep-v051-history-card [data-action="full-history"]')
        page.wait_for_function(
            "() => Boolean(window.__epPanel.shadowRoot.querySelector('.ep-v051-history-modal'))",
            timeout=10_000,
        )
        modal = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              const modal = root.querySelector('.ep-v051-history-modal');
              return {
                open: Boolean(modal),
                rows: modal?.querySelectorAll('tbody tr').length || 0,
                filter: modal ? getComputedStyle(modal).backdropFilter : '',
              };
            }
            """
        )
        result["modal_open"] = modal["open"]
        result["modal_rows"] = modal["rows"] >= 40
        result["modal_no_filter"] = modal["filter"] in {"", "none"}
        activate(page, profile, '.ep-v051-history-modal [data-action="close"]')
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-v051-history-modal')",
            timeout=10_000,
        )
        result["modal_closed"] = True

        page.evaluate(
            "window.__epSetEntityByKey('control_command', 'hybrid_grid_import')"
        )
        page.wait_for_function(
            "() => !window.__epPanel.__epV027BatteryPlanPromise",
            timeout=15_000,
        )
        stability = page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              return {
                card: window.__epV051HistoryIdentity.card === root.querySelector(
                  '.ep-v051-history-card'
                ),
                main: window.__epV051HistoryIdentity.main === root.querySelector('main'),
              };
            }
            """
        )
        result["card_stable"] = stability["card"]
        result["main_stable"] = stability["main"]
        result["ran"] = True
    except PlaywrightError as err:
        result["error"] = str(err)
    return result


def exercise_beta_tests(page: Page, profile: Profile) -> dict[str, object]:
    """Exercise the local-only control laboratory without touching HA services."""
    enabled = EXPECTED_ENTRYPOINT in {"v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "initially_hidden": False,
        "menu_entry": False,
        "opened": False,
        "dashboard_hidden": False,
        "touch_targets": False,
        "responsive": False,
        "methods": {},
        "controls": {},
        "telemetry_main_stable": False,
        "telemetry_tests_stable": False,
        "structural_tests_stable": False,
        "structural_open_preserved": False,
        "local_only": False,
        "closed": False,
        "dashboard_restored": False,
        "error": None,
    }
    if not enabled:
        return result

    try:
        before = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              window.__epBetaBrowserIdentity = {
                main: root.querySelector('main'),
                tests: panel.__epPermanentBetaTests,
              };
              return {
                service: window.__epServiceCalls.length,
                ws: window.__epWsCalls.length,
                testsHidden: Boolean(
                  panel.__epPermanentBetaTests?.hidden &&
                  getComputedStyle(panel.__epPermanentBetaTests).display === 'none'
                ),
              };
            }
            """
        )
        result["initially_hidden"] = before["testsHidden"]

        activate(page, profile, ".ep-layout-button")
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.shadowRoot.querySelector('.ep-layout-menu') &&
              window.__epPanel.shadowRoot.querySelector('.ep-beta-tests-menu')
            )
            """,
            timeout=10_000,
        )
        result["menu_entry"] = True
        activate(page, profile, ".ep-beta-tests-menu")
        page.wait_for_function(
            """
            () => {
              const panel = window.__epPanel;
              const tests = panel.__epPermanentBetaTests;
              return Boolean(
                tests && tests.isConnected && !tests.hidden &&
                tests.querySelector('[data-beta-control="native-range"]') &&
                tests.querySelector('ep-beta-shadow-button')?.shadowRoot?.querySelector('button') &&
                panel.shadowRoot.querySelector('main')?.hasAttribute(
                  'data-ep-beta-tests-open'
                )
              );
            }
            """,
            timeout=10_000,
        )
        opened = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const main = root.querySelector('main');
              const tests = panel.__epPermanentBetaTests;
              const activationTargets = [
                tests.querySelector('[data-beta-control="method-native-click"]'),
                tests.querySelector('[data-beta-control="method-pointerup-direct"]'),
                tests.querySelector('[data-beta-control="method-pointerup-delegated"]'),
                tests.querySelector('[data-beta-control="method-click-fallback"]'),
                tests.querySelector('[data-beta-control="method-pointerup-dedupe"]'),
              ];
              const visibleDashboardChildren = [...main.children].filter(
                child => child !== tests && !child.classList.contains('topbar') && !child.hidden
              );
              const rect = tests.getBoundingClientRect();
              return {
                opened: !tests.hidden,
                dashboardHidden: visibleDashboardChildren.length === 0,
                touchTargets: activationTargets.every(node => {
                  const target = node?.getBoundingClientRect();
                  return target && target.width >= 44 && target.height >= 44;
                }),
                responsive: tests.scrollWidth <= tests.clientWidth + 1 &&
                  rect.left >= -1 && rect.right <= innerWidth + 1,
              };
            }
            """
        )
        result["opened"] = opened["opened"]
        result["dashboard_hidden"] = opened["dashboardHidden"]
        result["touch_targets"] = opened["touchTargets"]
        result["responsive"] = opened["responsive"]

        method_controls = (
            '[data-beta-control="method-native-click"]',
            '[data-beta-control="method-pointerup-direct"]',
            '[data-beta-control="method-pointerup-delegated"]',
            '[data-beta-control="method-click-fallback"]',
            '[data-beta-control="method-pointerup-dedupe"]',
        )
        for selector in method_controls:
            for _index in range(20):
                activate(page, profile, selector)

        page.evaluate(
            """
            () => {
              const tests = window.__epPanel.__epPermanentBetaTests;
              const fallback = tests.querySelector(
                '[data-beta-control="method-click-fallback"]'
              );
              fallback.dispatchEvent(new PointerEvent('pointerdown', {
                bubbles: true, composed: true, pointerId: 901,
                pointerType: 'touch', isPrimary: true, clientX: 10, clientY: 10,
              }));
              fallback.dispatchEvent(new PointerEvent('pointerup', {
                bubbles: true, composed: true, pointerId: 901,
                pointerType: 'touch', isPrimary: true, clientX: 10, clientY: 10,
              }));

              const direct = tests.querySelector(
                '[data-beta-control="method-pointerup-direct"]'
              );
              direct.dispatchEvent(new PointerEvent('pointerdown', {
                bubbles: true, composed: true, pointerId: 902,
                pointerType: 'touch', isPrimary: true, clientX: 10, clientY: 10,
              }));
              direct.dispatchEvent(new PointerEvent('pointermove', {
                bubbles: true, composed: true, pointerId: 902,
                pointerType: 'touch', isPrimary: true, clientX: 10, clientY: 40,
              }));
              direct.dispatchEvent(new PointerEvent('pointerup', {
                bubbles: true, composed: true, pointerId: 902,
                pointerType: 'touch', isPrimary: true, clientX: 10, clientY: 40,
              }));
            }
            """
        )
        page.wait_for_timeout(200)

        page.evaluate(
            """
            () => {
              window.__epPanel.__epPermanentBetaTests.querySelector(
                '.ep-beta-tests-legacy'
              ).open = true;
            }
            """
        )

        repeated_controls = (
            '[data-beta-control="lit-button"]',
            '[data-beta-control="listener-button"]',
            '[data-beta-control="icon-button"]',
            'ep-beta-shadow-button button',
            '[data-beta-control="checkbox-switch"]',
            '[data-beta-card="label-switch"] .ep-beta-switch-row',
        )
        for selector in repeated_controls:
            for _index in range(20):
                activate(page, profile, selector)

        select = shadow(page, '[data-beta-control="native-select"]')
        for index in range(20):
            select.select_option(("b", "c", "a")[index % 3])

        range_control = shadow(page, '[data-beta-control="native-range"]')
        range_control.scroll_into_view_if_needed(timeout=5_000)
        range_control.focus()
        for index in range(20):
            range_control.press("ArrowRight" if index % 2 == 0 else "ArrowLeft")

        page.evaluate(
            """
            async () => {
              await window.__epPanel.__epPermanentBetaTests.updateComplete;
              await window.__epPanel.__epPermanentBetaTests.querySelector(
                'ep-beta-shadow-button'
              ).updateComplete;
            }
            """
        )
        snapshot = page.evaluate("window.__epBetaTests.snapshot()")
        result["methods"] = snapshot["methods"]
        result["controls"] = snapshot["controls"]

        page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              window.__epBetaTelemetryMain = panel.shadowRoot.querySelector('main');
              window.__epBetaTelemetryTests = panel.__epPermanentBetaTests;
              return window.__epTelemetryBurst(50, 4);
            }
            """
        )
        page.wait_for_timeout(500)
        telemetry = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              return {
                main: window.__epBetaTelemetryMain === panel.shadowRoot.querySelector('main'),
                tests: window.__epBetaTelemetryTests === panel.__epPermanentBetaTests &&
                  panel.__epPermanentBetaTests.isConnected &&
                  !panel.__epPermanentBetaTests.hidden,
              };
            }
            """
        )
        result["telemetry_main_stable"] = telemetry["main"]
        result["telemetry_tests_stable"] = telemetry["tests"]

        page.evaluate(
            """
            () => {
              window.__epBetaStructuralTests = window.__epPanel.__epPermanentBetaTests;
              window.__epPanel._queueRender();
            }
            """
        )
        page.wait_for_function(
            """
            () => Boolean(
              !window.__epPanel._renderQueued &&
              window.__epPanel.__epPermanentBetaTests?.isConnected
            )
            """,
            timeout=10_000,
        )
        structural = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const tests = panel.__epPermanentBetaTests;
              return {
                stable: window.__epBetaStructuralTests === tests,
                open: !tests.hidden && panel.__epBetaTestsOpen === true,
              };
            }
            """
        )
        result["structural_tests_stable"] = structural["stable"]
        result["structural_open_preserved"] = structural["open"]

        activate(page, profile, ".ep-beta-tests-close")
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.__epPermanentBetaTests?.hidden &&
              !window.__epPanel.shadowRoot.querySelector('main')?.hasAttribute(
                'data-ep-beta-tests-open'
              )
            )
            """,
            timeout=10_000,
        )
        after = page.evaluate(
            """
            () => {
              const panel = window.__epPanel;
              const root = panel.shadowRoot;
              const firstCard = root.querySelector('[data-ep-card]');
              return {
                service: window.__epServiceCalls.length,
                ws: window.__epWsCalls.length,
                restored: Boolean(firstCard && !firstCard.hidden),
                closed: Boolean(
                  panel.__epPermanentBetaTests.hidden &&
                  getComputedStyle(panel.__epPermanentBetaTests).display === 'none'
                ),
              };
            }
            """
        )
        result["local_only"] = (
            after["service"] == before["service"] and after["ws"] == before["ws"]
        )
        result["closed"] = after["closed"]
        result["dashboard_restored"] = after["restored"]
    except (PlaywrightError, RuntimeError) as err:
        result["error"] = str(err)
    return result


def exercise_touch_click_fallback(page: Page, profile: Profile) -> dict[str, object]:
    """Prove missing iOS clicks recover once across controls and menus."""
    enabled = EXPECTED_ENTRYPOINT in {"v110", "v130"}
    result: dict[str, object] = {
        "ran": enabled,
        "installed": False,
        "operational_fallback": False,
        "late_click_deduped": False,
        "movement_rejected": False,
        "cancel_rejected": False,
        "menu_opened": False,
        "menu_switch": False,
        "menu_reset": False,
        "beta_opened": False,
        "beta_raw_control_excluded": False,
        "beta_closed": False,
        "settings_opened": False,
        "settings_tab": False,
        "settings_closed": False,
        "chart_touch_targets": False,
        "chart_controls_fit": False,
        "chart_size_fallback": False,
        "chart_range_fallback": False,
        "history_fallback": False,
        "history_close_fallback": False,
        "metrics": {},
        "error": None,
    }
    if not enabled:
        return result

    try:
        page.evaluate(
            """
            () => {
              window.__epTouchClickFallback.reset();
              window.__epResetActionLogs();
              window.__epSetEntityByKey('automatic_control', 'off');
              window.__epSetEntityByKey('control_command', 'battery_pause');
              window.__epMissingTouchSequence = 1200;
              window.__epDispatchMissingTouch = async (selector, options = {}) => {
                const root = window.__epPanel.shadowRoot;
                const node = root.querySelector(selector);
                if (!node) throw new Error(`Missing touch target: ${selector}`);
                const pointerId = ++window.__epMissingTouchSequence;
                const common = {
                  bubbles: true,
                  composed: true,
                  pointerId,
                  pointerType: 'touch',
                  isPrimary: true,
                  button: 0,
                  clientX: 24,
                  clientY: 24,
                };
                node.dispatchEvent(new PointerEvent('pointerdown', common));
                if (options.move) {
                  node.dispatchEvent(new PointerEvent('pointermove', {
                    ...common,
                    clientY: 64,
                  }));
                }
                node.dispatchEvent(new PointerEvent(
                  options.cancel ? 'pointercancel' : 'pointerup',
                  options.move ? {...common, clientY: 64} : common,
                ));
                await new Promise(resolve => setTimeout(resolve, 180));
                if (options.lateClick) {
                  node.dispatchEvent(new MouseEvent('click', {
                    bubbles: true,
                    composed: true,
                    cancelable: true,
                    detail: 1,
                  }));
                  await new Promise(resolve => setTimeout(resolve, 40));
                }
                return node;
              };
            }
            """
        )
        page.wait_for_timeout(120)
        result["installed"] = page.evaluate(
            "() => window.__epTouchClickFallback?.snapshot?.().enabled === true"
        )

        quick_id = page.evaluate("window.__epPanel._entityId('max_charge')")
        page.evaluate(
            "window.__epDispatchMissingTouch('[data-action=\"max_charge\"]', {lateClick:true})"
        )
        wait_service_count(page, quick_id, 1)
        page.wait_for_timeout(100)
        quick_calls = page.evaluate(
            """
            entityId => window.__epServiceCalls.filter(
              call => call.data?.entity_id === entityId
            ).length
            """,
            quick_id,
        )
        result["operational_fallback"] = quick_calls == 1
        result["late_click_deduped"] = (
            quick_calls == 1
            and page.evaluate(
                "() => window.__epTouchClickFallback.snapshot().metrics.late_clicks_suppressed"
            )
            == 1
        )

        page.evaluate(
            "window.__epDispatchMissingTouch('.ep-layout-button', {move:true})"
        )
        result["movement_rejected"] = not page.evaluate(
            "() => Boolean(window.__epPanel.shadowRoot.querySelector('.ep-layout-menu'))"
        )
        page.evaluate(
            "window.__epDispatchMissingTouch('.ep-layout-button', {cancel:true})"
        )
        result["cancel_rejected"] = not page.evaluate(
            "() => Boolean(window.__epPanel.shadowRoot.querySelector('.ep-layout-menu'))"
        )

        page.evaluate(
            "window.__epDispatchMissingTouch('.ep-layout-button', {lateClick:true})"
        )
        page.wait_for_function(
            "() => Boolean(window.__epPanel.shadowRoot.querySelector('.ep-layout-menu'))",
            timeout=2_000,
        )
        result["menu_opened"] = True
        switch_before = page.evaluate(
            "() => window.__epPanel.shadowRoot.querySelector('[data-ep-visible=\"solar\"]')?.checked"
        )
        page.evaluate(
            "window.__epDispatchMissingTouch('[data-ep-visible=\"solar\"]')"
        )
        page.wait_for_timeout(100)
        switch_after = page.evaluate(
            "() => window.__epPanel.shadowRoot.querySelector('[data-ep-visible=\"solar\"]')?.checked"
        )
        result["menu_switch"] = switch_after is not None and switch_after != switch_before

        page.evaluate("window.__epDispatchMissingTouch('.ep-menu-reset')")
        page.wait_for_timeout(100)
        result["menu_reset"] = page.evaluate(
            "() => window.__epPanel.shadowRoot.querySelector('[data-ep-visible=\"solar\"]')?.checked === true"
        )
        page.evaluate("window.__epDispatchMissingTouch('.ep-beta-tests-menu')")
        page.wait_for_function(
            "() => window.__epPanel.__epBetaTestsOpen === true",
            timeout=2_000,
        )
        result["beta_opened"] = True
        raw_before = page.evaluate(
            "() => window.__epBetaTests.snapshot().methods['method-native-click'].metrics.actions"
        )
        page.evaluate(
            "window.__epDispatchMissingTouch('[data-beta-control=\"method-native-click\"]')"
        )
        raw_after = page.evaluate(
            "() => window.__epBetaTests.snapshot().methods['method-native-click'].metrics.actions"
        )
        result["beta_raw_control_excluded"] = raw_after == raw_before
        page.evaluate("window.__epDispatchMissingTouch('.ep-beta-tests-close')")
        page.wait_for_function(
            "() => window.__epPanel.__epBetaTestsOpen !== true",
            timeout=2_000,
        )
        result["beta_closed"] = True

        page.evaluate("window.__epDispatchMissingTouch('.ep-v016-settings-button')")
        page.wait_for_function(
            "() => Boolean(window.__epPanel.shadowRoot.querySelector('.ep-v016-settings'))",
            timeout=5_000,
        )
        result["settings_opened"] = True
        page.evaluate(
            "window.__epDispatchMissingTouch('[data-settings-tab=\"goodwe\"]')"
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '[data-settings-tab="goodwe"]'
            )?.classList.contains('active')
            """,
            timeout=2_000,
        )
        result["settings_tab"] = True
        page.evaluate("window.__epDispatchMissingTouch('.ep-v016-back')")
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-v016-settings')",
            timeout=2_000,
        )
        result["settings_closed"] = True

        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.__epV027BatteryPlanData &&
              !window.__epPanel.__epV027BatteryPlanPromise &&
              window.__epPanel.shadowRoot.querySelector('[data-chart-size="compact"]') &&
              window.__epPanel.shadowRoot.querySelector('[data-chart-range="12h"]') &&
              window.__epPanel.shadowRoot.querySelector('[data-action="full-history"]')
            )
            """,
            timeout=10_000,
        )
        if profile.touch:
            touch_layout = page.evaluate(
                """
                () => {
                  const root = window.__epPanel.shadowRoot;
                  const card = root.querySelector('.ep-v027-battery-plan-card');
                  const actions = card?.querySelector('.ep-v027-head-actions');
                  const targets = [
                    '[data-chart-size="compact"]',
                    '[data-chart-size="normal"]',
                    '[data-chart-size="large"]',
                    '[data-chart-range="12h"]',
                    '[data-chart-range="24h"]',
                    '[data-chart-range="36h"]',
                    '[data-action="full-history"]',
                  ].every((selector) => {
                    const rect = root.querySelector(selector)?.getBoundingClientRect();
                    return Boolean(rect && rect.width >= 44 && rect.height >= 44);
                  });
                  return {
                    targets,
                    fits: Boolean(card && actions) &&
                      card.scrollWidth <= card.clientWidth + 1 &&
                      actions.scrollWidth <= actions.clientWidth + 1,
                  };
                }
                """
            )
            result["chart_touch_targets"] = touch_layout["targets"]
            result["chart_controls_fit"] = touch_layout["fits"]
        else:
            result["chart_touch_targets"] = True
            result["chart_controls_fit"] = True

        page.evaluate(
            """
            () => {
              const root = window.__epPanel.shadowRoot;
              window.__epMissingChartClicks = Object.create(null);
              const targets = {
                compact: '[data-chart-size="compact"]',
                normal: '[data-chart-size="normal"]',
                range12: '[data-chart-range="12h"]',
                range24: '[data-chart-range="24h"]',
                range36: '[data-chart-range="36h"]',
                full: '[data-action="full-history"]',
              };
              for (const [key, selector] of Object.entries(targets)) {
                window.__epMissingChartClicks[key] = 0;
                root.querySelector(selector)?.addEventListener('click', () => {
                  window.__epMissingChartClicks[key] += 1;
                });
              }
            }
            """
        )
        page.evaluate(
            "window.__epDispatchMissingTouch('[data-chart-size=\"compact\"]', {lateClick:true})"
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v027-battery-plan-card'
            )?.classList.contains('size-compact')
            """,
            timeout=2_000,
        )
        page.evaluate(
            "window.__epDispatchMissingTouch('[data-chart-size=\"normal\"]')"
        )
        page.wait_for_function(
            """
            () => window.__epPanel.shadowRoot.querySelector(
              '.ep-v027-battery-plan-card'
            )?.classList.contains('size-normal')
            """,
            timeout=2_000,
        )
        result["chart_size_fallback"] = page.evaluate(
            """
            () => window.__epMissingChartClicks.compact === 1 &&
              window.__epMissingChartClicks.normal === 1
            """
        )

        for value in ("12h", "36h", "24h"):
            page.evaluate(
                f"window.__epDispatchMissingTouch('[data-chart-range=\"{value}\"]')"
            )
            page.wait_for_function(
                "() => window.__epPanel.shadowRoot.querySelector("
                f"'[data-chart-range=\"{value}\"]'"
                ")?.getAttribute('aria-pressed') === 'true'",
                timeout=2_000,
            )
        result["chart_range_fallback"] = page.evaluate(
            """
            () => window.__epMissingChartClicks.range12 === 1 &&
              window.__epMissingChartClicks.range36 === 1 &&
              window.__epMissingChartClicks.range24 === 1
            """
        )

        page.evaluate(
            "window.__epDispatchMissingTouch('[data-action=\"full-history\"]', {lateClick:true})"
        )
        page.wait_for_function(
            """
            () => Boolean(window.__epPanel.shadowRoot.querySelector(
              '.ep-v051-history-modal'
            ))
            """,
            timeout=2_000,
        )
        result["history_fallback"] = page.evaluate(
            "() => window.__epMissingChartClicks.full === 1"
        )
        page.evaluate(
            "window.__epDispatchMissingTouch('.ep-v051-history-modal [data-action=\"close\"]', {lateClick:true})"
        )
        page.wait_for_function(
            "() => !window.__epPanel.shadowRoot.querySelector('.ep-v051-history-modal')",
            timeout=2_000,
        )
        result["history_close_fallback"] = True
        result["metrics"] = page.evaluate(
            "() => window.__epTouchClickFallback.snapshot().metrics"
        )
    except (PlaywrightError, RuntimeError) as err:
        result["error"] = str(err)
    return result


def exercise_profile(page: Page, profile: Profile) -> dict[str, object]:
    page.goto(HARNESS, wait_until="domcontentloaded", timeout=30_000)
    page.evaluate("window.__epReady")
    try:
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
    except PlaywrightError as err:
        bootstrap = page.evaluate(
            """
            () => ({
              ready: Boolean(window.__epReady),
              entrypoint: window.__epEntryPoint || '',
              panel: Boolean(window.__epPanel),
              shadow: Boolean(window.__epPanel?.shadowRoot),
              layout: Boolean(window.__epPanel?.shadowRoot?.querySelector('.ep-layout-button')),
              automatic: Boolean(window.__epPanel?.shadowRoot?.querySelector('#auto-toggle')),
              cards: window.__epPanel?.shadowRoot?.querySelectorAll('[data-ep-card]').length ?? -1,
              html: window.__epPanel?.shadowRoot?.innerHTML?.slice(0, 180) || '',
              errors: window.__epErrors || [],
            })
            """
        )
        raise RuntimeError(f"dashboard bootstrap timed out: {bootstrap}") from err
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
            help: root.querySelector('.ep-v016-help-button'),
          };
          const max = scroller.scrollHeight - scroller.clientHeight;
          scroller.scrollTop = Math.max(0, Math.round(max * 0.55));
          return {
            entrypoint: window.__epEntryPoint,
            controlArchitecture: Boolean(window.__epPanel.__epControlSurfaceArchitecture),
            releaseVersion: root.querySelector('.version')?.textContent?.trim() || '',
            hybridNote: root.querySelector('.ep-v022-strategy-note')?.textContent?.trim() || '',
            stableMarker: root.querySelector('main')?.dataset.epV041StableDom || '',
            scrollTop: scroller.scrollTop,
            scrollHeight: scroller.scrollHeight,
            clientHeight: scroller.clientHeight,
            max,
            cards: root.querySelectorAll('[data-ep-card]').length,
            buttons: root.querySelectorAll('button').length,
            helpHref: root.querySelector('.ep-v016-help-button')?.href || '',
            helpTarget: root.querySelector('.ep-v016-help-button')?.target || '',
            helpRel: root.querySelector('.ep-v016-help-button')?.rel || '',
            helpAria: root.querySelector('.ep-v016-help-button')?.getAttribute('aria-label') || '',
            helpSize: (() => {
              const help = root.querySelector('.ep-v016-help-button');
              const rect = help?.getBoundingClientRect();
              return rect ? {width: rect.width, height: rect.height} : {width: 0, height: 0};
            })(),
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
            help:
              window.__epTelemetryIdentity.help === root.querySelector('.ep-v016-help-button'),
          };
        }
        """
    )

    strategy_note = exercise_strategy_note_stability(page)
    setpoint_update = exercise_setpoint_update(page)
    emhass_mapping = exercise_emhass_mapping(page)
    static_flow = exercise_static_flow(page)
    connectivity = exercise_connectivity_status(page, profile)
    ev_protection = exercise_ev_protection_banner(page)

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
    deadband_settings = exercise_deadband_settings(page, profile)
    sems_settings = exercise_sems_settings(page, profile)
    pv_settings = exercise_pv_settings(page, profile)
    ev_settings = exercise_ev_settings(page, profile)
    host_property_press = exercise_host_property_press(page, profile)
    live_copy_press = exercise_live_copy_press(page, profile)
    quick_action_state = exercise_quick_action_state(page, profile)
    selector_stability = exercise_selector_stability(page, profile)
    touch_controls = exercise_touch_controls(page, profile)
    optimize_stability = exercise_optimize_stability(page, profile)
    menu = open_and_close_menu(page)
    automatic = exercise_automatic_control(page)
    emhass_overview_controls = exercise_emhass_overview_controls(page)
    soc_slider = exercise_soc_slider_draft(page)
    strategy = exercise_strategy(page)
    chart_size_press = exercise_chart_size_press(page, profile)
    chart_range_press = exercise_chart_range_press(page, profile)
    plan = exercise_plan_refresh(page)
    execution_history = exercise_execution_history(page, profile)
    beta_tests = exercise_beta_tests(page, profile)
    touch_click_fallback = exercise_touch_click_fallback(page, profile)
    language_result = exercise_language(page)
    structural = exercise_structural_rerender(page)

    return {
        "profile": profile.name,
        "initial": initial,
        "idle_before": idle_before,
        "idle_after": idle_after,
        "idle_delta": idle_after - idle_before,
        "telemetry_identity": telemetry_identity,
        "strategy_note": strategy_note,
        "setpoint_update": setpoint_update,
        "emhass_mapping": emhass_mapping,
        "static_flow": static_flow,
        "connectivity": connectivity,
        "ev_protection": ev_protection,
        "motion": motion,
        "pv_insight": pv_insight,
        "deadband_settings": deadband_settings,
        "sems_settings": sems_settings,
        "pv_settings": pv_settings,
        "ev_settings": ev_settings,
        "host_property_press": host_property_press,
        "live_copy_press": live_copy_press,
        "quick_action_state": quick_action_state,
        "selector_stability": selector_stability,
        "touch_controls": touch_controls,
        "optimize_stability": optimize_stability,
        "menu": menu,
        "automatic": automatic,
        "emhass_overview_controls": emhass_overview_controls,
        "soc_slider": soc_slider,
        "strategy": strategy,
        "chart_size_press": chart_size_press,
        "chart_range_press": chart_range_press,
        "plan": plan,
        "execution_history": execution_history,
        "beta_tests": beta_tests,
        "touch_click_fallback": touch_click_fallback,
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
    control_architecture = bool(initial.get("controlArchitecture"))
    identity = result["telemetry_identity"]
    strategy_note = result["strategy_note"]
    setpoint_update = result["setpoint_update"]
    emhass_mapping = result["emhass_mapping"]
    static_flow = result["static_flow"]
    connectivity = result["connectivity"]
    ev_protection = result["ev_protection"]
    motion = result["motion"]
    pv_insight = result["pv_insight"]
    deadband_settings = result["deadband_settings"]
    sems_settings = result["sems_settings"]
    pv_settings = result["pv_settings"]
    ev_settings = result["ev_settings"]
    host_property_press = result["host_property_press"]
    live_copy_press = result["live_copy_press"]
    quick_action_state = result["quick_action_state"]
    selector_stability = result["selector_stability"]
    touch_controls = result["touch_controls"]
    optimize_stability = result["optimize_stability"]
    menu = result["menu"]
    automatic = result["automatic"]
    emhass_overview_controls = result["emhass_overview_controls"]
    soc_slider = result["soc_slider"]
    strategy = result["strategy"]
    chart_size_press = result["chart_size_press"]
    chart_range_press = result["chart_range_press"]
    plan = result["plan"]
    execution_history = result["execution_history"]
    beta_tests = result["beta_tests"]
    touch_click_fallback = result["touch_click_fallback"]
    language_result = result["language"]
    structural = result["structural"]
    animation = result["animation"]

    if EXPECTED_ENTRYPOINT and initial["entrypoint"] != EXPECTED_ENTRYPOINT:
        failures.append(f"{name}: loaded {initial['entrypoint']} instead of {EXPECTED_ENTRYPOINT}")
    expected_badge = {
        "v045": "v0.45 BETA",
        "v046": "v0.46 BETA",
        "v047": "v0.47 BETA",
        "v048": "v0.48 BETA",
        "v049": "v0.49 BETA",
        "v050": "v0.50 BETA",
        "v051": "v0.51 BETA",
        "v100": "v1.0.0 STABLE",
        "v101": "v1.0.1-beta.4 BETA",
        "v110": "v1.2.0 STABLE",
        "v130": "v1.3.0-beta.1 BETA",
    }.get(EXPECTED_ENTRYPOINT)
    if expected_badge and initial["releaseVersion"] != expected_badge:
        failures.append(
            f"{name}: release badge is {initial['releaseVersion']!r} instead of {expected_badge}"
        )
    if EXPECTED_ENTRYPOINT in {"v110", "v130"}:
        if not (
            initial["helpHref"].endswith("/docs/USER_GUIDE.md")
            and initial["helpTarget"] == "_blank"
            and "noopener" in initial["helpRel"]
            and "noreferrer" in initial["helpRel"]
            and initial["helpAria"] == "Open GW EnergyPilot user guide"
        ):
            failures.append(f"{name}: localized header help link is missing or unsafe")
        minimum_help_size = 44 if profile.touch else 38
        if (
            initial["helpSize"]["width"] + 0.5 < minimum_help_size
            or initial["helpSize"]["height"] + 0.5 < minimum_help_size
        ):
            failures.append(f"{name}: header help target is smaller than {minimum_help_size}px")
        if identity["help"] is not True:
            failures.append(f"{name}: telemetry replaced the header help link")
    hybrid_phrases = (
        (
            "Battery Hold deadband on P_batt",
            "separate GoodWe Auto deadband",
            "modes 9/10 outside it",
            "full grid target as setpoint",
        )
        if EXPECTED_ENTRYPOINT in {"v101", "v110", "v130"}
        else (
            "neutral P_batt plan in mode 8",
            "mode 1 inside the configured deadband",
            "modes 9/10 outside it",
            "full grid target as setpoint",
        )
    )
    if EXPECTED_ENTRYPOINT in {"v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"} and not all(
        phrase in initial["hybridNote"] for phrase in hybrid_phrases
    ):
        failures.append(f"{name}: active Hybrid operator copy is stale")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS and initial["stableMarker"] != "1":
        failures.append(f"{name}: stable-DOM marker is missing")
    if initial["max"] < 500:
        failures.append(f"{name}: harness is not sufficiently scrollable")
    if initial["cards"] < 8 or initial["buttons"] < 20:
        failures.append(f"{name}: dashboard controls/cards did not initialize completely")
    if abs(result["idle_delta"]) > 2:
        failures.append(f"{name}: idle telemetry moved scroll by {result['idle_delta']} px")
    if EXPECTED_ENTRYPOINT in {"v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}:
        required_strategy_note = (
            "ran", "present", "note_stable", "strong_stable", "height_stable",
            "no_child_rebuilds", "dutch_copy", "context_refresh",
        )
        if not all(strategy_note[key] is True for key in required_strategy_note):
            failures.append(
                f"{name}: Hybrid strategy note rebuild/layout regression failed: "
                f"{strategy_note}"
            )
        if strategy_note["error"]:
            failures.append(f"{name}: Hybrid strategy note interaction error")
    if not all(
        setpoint_update.get(key)
        for key in ("present", "changed", "stableMain", "stableMetric")
    ):
        failures.append(
            f"{name}: EMS setpoint update evidence is missing or rebuilt: {setpoint_update}"
        )
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS and not all(
        emhass_mapping.get(key) is True
        for key in ("ran", "mode1", "mode10", "stable")
    ):
        failures.append(
            f"{name}: EMHASS mapping diverged from the backend controller decision: "
            f"{emhass_mapping}"
        )
    expected_initial = {
        "pv": ("active", "right", "high", "→"),
        "grid": ("active", "right", "low", "→"),
        "house": ("active", "up", "medium", "↑"),
        "battery": ("active", "down", "low", "↓"),
    }
    for key, expected in expected_initial.items():
        state = static_flow["initial"][key]
        actual = (
            state["status"], state["direction"], state["intensity"], state["arrow"]
        )
        if actual != expected:
            failures.append(f"{name}: initial {key} flow {actual} != {expected}")
        if (
            state["role"] != "img"
            or not state["label"]
            or "relative flow" not in state["label"]
            or state["arrowDisplay"] != "flex"
            or state["arrowBorder"] != "none"
            or "polygon" not in state["arrowClipPath"]
            or state["arrowFontSize"] != 0
            or "gradient" not in state["trackMask"]
            or state["stateDisplay"] != "none"
            or not state["inside"]
        ):
            failures.append(f"{name}: initial {key} flow is not visible/accessibly labelled")
    if static_flow["initial"]["pv"]["thickness"] < 5:
        failures.append(f"{name}: high flow does not use a strong pipeline")
    if static_flow["initial"]["house"]["thickness"] < 3:
        failures.append(f"{name}: medium flow does not use a distinct pipeline")
    if static_flow["initial"]["grid"]["thickness"] > 3:
        failures.append(f"{name}: low flow pipeline is not visually bounded")
    if (
        static_flow["reversed"]["grid"]["direction"] != "left"
        or static_flow["reversed"]["grid"]["arrow"] != "←"
        or static_flow["reversed"]["battery"]["direction"] != "up"
        or static_flow["reversed"]["battery"]["arrow"] != "↑"
    ):
        failures.append(f"{name}: import/discharge physical direction is wrong")
    for key, state in static_flow["unknown"].items():
        if (
            state["status"] != "unknown"
            or state["intensity"] != "none"
            or state["state"] != "?"
            or state["stateDisplay"] != "flex"
            or "unavailable" not in state["label"]
        ):
            failures.append(f"{name}: {key} unknown flow presentation is ambiguous")
    for key, state in static_flow["idle"].items():
        if (
            state["status"] != "idle"
            or state["intensity"] != "none"
            or state["state"] != "•"
            or state["stateDisplay"] != "flex"
            or "idle below 50 W" not in state["label"]
        ):
            failures.append(f"{name}: {key} near-zero flow presentation is ambiguous")
    if not all(static_flow["identity"].values()):
        failures.append(f"{name}: flow telemetry replaced stable DOM nodes")
    if not static_flow["responsive"]:
        failures.append(f"{name}: flow overview overflows its responsive container")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS:
        required_connectivity = (
            "ran", "placed", "initial_ok", "details_open", "issue_visible",
            "unknown_visible", "countdown_visible", "main_stable",
            "button_stable", "restored", "above_card_controls",
            "pointer_isolated", "hit_isolated",
        )
        if not all(connectivity[key] is True for key in required_connectivity):
            failures.append(f"{name}: connectivity status stable-DOM regression failed")
        if connectivity["error"]:
            failures.append(f"{name}: connectivity status interaction error")
    for key, stable in identity.items():
        if stable is not True:
            failures.append(f"{name}: telemetry replaced the {key} DOM node")
    if motion["backwards"] != 0:
        failures.append(f"{name}: scroll moved backwards during telemetry")
    if abs(motion["final"] - motion["target"]) > 5:
        failures.append(f"{name}: scrolling did not reach its target during telemetry")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS:
        required_ev_protection = (
            "present", "initial_hidden", "blocking", "allowing", "waiting",
            "inactive_hidden", "main_stable", "banner_stable", "non_interactive",
        )
        if not all(ev_protection[key] is True for key in required_ev_protection):
            failures.append(f"{name}: EV protection banner state/stability regression failed")
        if ev_protection["error"]:
            failures.append(f"{name}: EV protection banner interaction error")
        pv_required = (
            "ran", "total_matches", "flow_matches", "split_nodes", "routes_match",
            "telemetry_main_stable", "external_value_matches", "flow_values_match",
            "flow_nodes_stable",
        ) if control_architecture else (
            "ran", "topology_rendered", "total_matches", "flow_matches",
            "split_nodes", "routes_match", "telemetry_main_stable",
            "external_value_matches", "flow_values_match", "flow_nodes_stable",
        )
        if not all(pv_insight[key] is True for key in pv_required) or pv_insight["source_count"] != 2:
            failures.append(f"{name}: combined PV topology/live patch regression failed")
        if abs(pv_insight["scroll_delta"] or 0) > 2:
            failures.append(f"{name}: PV telemetry moved scroll position")
        if pv_insight["error"]:
            failures.append(f"{name}: PV insight interaction error")
        if not all(
            pv_settings[key] is True
            for key in (
                "ran", "tab_present", "internal_checked", "external_checked",
                "fields_grouped", "disabled_when_off", "enabled_when_on",
                "value_preserved",
                "entity_search_contains_source", "closed",
            )
        ) or pv_settings["external_fields"] != 4:
            failures.append(f"{name}: PV settings tab/entity-search regression failed")
        if pv_settings["error"]:
            failures.append(f"{name}: PV settings interaction error")
    if EXPECTED_ENTRYPOINT in {"v101", "v110", "v130"} and not all(
        deadband_settings.get(key) is True
        for key in (
            "ran", "inputs_present", "defaults_correct", "zero_centered",
            "directions_present", "modes_correct", "invalid_blocked",
            "valid_restored", "submitted_both", "responsive_fit", "closed",
        )
    ):
        failures.append(
            f"{name}: EP deadband settings panel or validation regressed: "
            f"{deadband_settings}"
        )
    if deadband_settings["error"]:
        failures.append(f"{name}: EP deadband settings interaction error")
    if EXPECTED_ENTRYPOINT in {"v110", "v130"} and not all(
        sems_settings.get(key) is True
        for key in (
            "ran", "tab_present", "choices_present",
            "sems_disabled_in_local_mode", "sems_enabled_in_cloud_mode",
            "local_control_stays_enabled", "password_protected",
            "boundary_copy_present", "submitted_complete", "closed",
        )
    ):
        failures.append(
            f"{name}: SEMS telemetry settings/control boundary regressed: "
            f"{sems_settings}"
        )
    if sems_settings["error"]:
        failures.append(f"{name}: SEMS settings interaction error")
    if EXPECTED_ENTRYPOINT in {"v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}:
        if not all(
            ev_settings[key] is True
            for key in (
                "ran", "tab_present", "detection_choice_present",
                "power_source_exclusive", "status_source_exclusive",
                "detection_submitted", "profiles_present", "recommended_window",
                "feedback_entity_present", "manual_grid_current_removed",
                "goodwe_source_present", "charger_entity_present",
                "warning_prominent", "confirmation_sent", "closed",
            )
        ):
            failures.append(f"{name}: EV load-balancing settings safety regression failed")
        if ev_settings["error"]:
            failures.append(f"{name}: EV settings interaction error")
    if EXPECTED_ENTRYPOINT in {"v045", "v046", "v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}:
        required_host_press = (
            "ran", "no_full_render", "main_stable", "controls_stable",
            "native_click", "touch_click", "real_panel_change",
        )
        if not all(host_property_press[key] is True for key in required_host_press):
            failures.append(f"{name}: Home Assistant host update interrupted a control press")
        if host_property_press["error"]:
            failures.append(f"{name}: host-property press interaction error")
        if EXPECTED_ENTRYPOINT in {"v101", "v110", "v130"}:
            required_live_copy_press = (
                "ran", "optimize_click", "costfun_click",
                "optimize_copy_stable", "costfun_copy_stable",
                "no_full_render", "main_stable", "controls_stable",
            )
            if not all(
                live_copy_press[key] is True for key in required_live_copy_press
            ):
                failures.append(
                    f"{name}: live button-copy patch interrupted a physical press"
                )
            if live_copy_press["error"]:
                failures.append(f"{name}: live button-copy press interaction error")
        required_quick_state = (
            "ran", "event_ordering", "pressed_semantics", "inactive_auto_neutral",
            "no_full_render", "main_stable", "button_stable", "delayed_publication",
        )
        if not all(quick_action_state[key] is True for key in required_quick_state):
            failures.append(f"{name}: Battery quick-action stable-state regression failed")
        if quick_action_state["error"]:
            failures.append(f"{name}: Battery quick-action state interaction error")
        required_selector_stability = (
            "ran", "costfun_delayed", "costfun_external", "costfun_busy_lock",
            "manual_unlocked", "manual_called", "no_full_render", "main_stable",
            "controls_stable",
        )
        if control_architecture:
            required_selector_stability = tuple(
                key for key in required_selector_stability if key != "costfun_busy_lock"
            )
        if not all(
            selector_stability[key] is True
            for key in required_selector_stability
        ):
            failures.append(f"{name}: stable selector feedback regression failed")
        if selector_stability["error"]:
            failures.append(f"{name}: stable selector feedback interaction error")
    if profile.touch and not control_architecture and EXPECTED_ENTRYPOINT in {"v043", "v044", "v045", "v046", "v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}:
        required_touch = (
            "ran", "touch_media", "optimize", "emhass", "battery",
            "quick_actions", "menu_cycles", "hover_reset",
            "render_during_press", "post_structure", "telemetry_complete",
        )
        if not all(touch_controls[key] is True for key in required_touch):
            failures.append(f"{name}: repeated touch-control regression failed")
        if touch_controls["error"]:
            failures.append(f"{name}: touch-control interaction error")
    if EXPECTED_ENTRYPOINT in {"v044", "v045", "v046", "v047", "v048", "v049", "v050", "v051", "v100", "v101", "v110", "v130"}:
        required_optimize = (
            "ran", "single_call", "no_full_render", "main_stable",
            "optimize_stable", "layout_stable", "automatic_stable",
            "strategy_stable", "scroll_anchor_stable", "button_position_stable",
            "floating", "viewport_reachable", "safe_edge_spacing", "touch_target",
            "outside_optional_card", "visible_with_card_hidden", "footer_clear",
            "scroll_working", "button_idle", "marker",
        )
        if control_architecture:
            required_optimize = (
                "ran", "single_call", "no_full_render", "main_stable",
                "optimize_stable", "layout_stable", "automatic_stable",
                "strategy_stable", "touch_target", "visible_with_card_hidden",
                "scroll_working", "button_idle",
            )
        if not all(optimize_stability[key] is True for key in required_optimize):
            failures.append(f"{name}: Optimize now rebuilt or moved interaction DOM")
        if optimize_stability["error"]:
            failures.append(f"{name}: Optimize now stability interaction error")
    if menu["open"] is not True or menu["close"] is not True:
        failures.append(f"{name}: dashboard menu did not reliably open and close")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS and not all(
        menu[key] is True
        for key in (
            "motion_available", "motion_default_on", "motion_off",
            "motion_on", "motion_reduced",
        )
    ):
        failures.append(f"{name}: scoped flow-motion preference regressed: {menu}")
    if menu["error"]:
        failures.append(f"{name}: dashboard menu interaction error")
    if not control_architecture and not all(
        automatic[key] is True
        for key in (
            "present", "compact_on", "off_changed", "controls_shown_off",
            "off_nodes_stable", "on_changed", "compact_restored_on",
            "on_nodes_stable", "manual_mode_worked", "focus_rehomed",
            "final_on", "main_stable",
        )
    ):
        failures.append(
            f"{name}: compact manual controls did not toggle or operate stably"
        )
    if automatic["error"] and not control_architecture:
        failures.append(f"{name}: Automatic Control interaction error")
    if emhass_overview_controls != {
        "legacySocCount": 0,
        "permanentSocCount": 2,
        "profit": ["profit"],
        "cost": ["cost"],
        "restoredLegacySocCount": 0,
    }:
        failures.append(
            f"{name}: EMHASS overview ownership/selection mismatch: "
            f"{emhass_overview_controls}"
        )
    if not control_architecture and EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS and not all(
        soc_slider[key] is True
        for key in (
            "present", "slider_kept_draft", "label_kept_draft", "acknowledged",
            "custom_values_saved", "custom_main_stable", "custom_typography_larger",
        )
    ):
        failures.append(
            f"{name}: custom Battery Strategy editing or SOC draft stability regressed"
        )
    if soc_slider["error"] and not control_architecture:
        failures.append(f"{name}: SOC slider interaction error")
    if strategy["present"] is not True or strategy["changed"] is not True:
        failures.append(f"{name}: Battery Strategy button did not apply")
    if EXPECTED_ENTRYPOINT in {"v110", "v130"} and not (
        strategy["profile_choices"] == 6
        and strategy["chargegasm_present"] is True
        and strategy["managed_summary"] is True
        and strategy["custom_sliders_absent"] is True
    ):
        failures.append(
            f"{name}: managed profile summary, Chargegasm or slider visibility regressed"
        )
    if strategy["error"]:
        failures.append(f"{name}: Battery Strategy interaction error")
    if EXPECTED_ENTRYPOINT in {"v047", "v051", "v100", "v101", "v110", "v130"} and not all(
        chart_size_press[key] is True
        for key in (
            "ran", "refresh_during_press", "click_delivered", "size_selected",
            "preference_saved", "single_card", "main_stable", "card_stable",
            "header_stable", "button_stable", "window_bar_present",
            "window_bar_stable", "restored_normal",
        )
    ):
        failures.append(f"{name}: plan refresh interrupted an S/M/L chart-size press")
    if chart_size_press["error"]:
        failures.append(f"{name}: chart-size press interaction error")
    if EXPECTED_ENTRYPOINT in {"v050", "v110", "v130"} and not all(
        chart_range_press[key] is True
        for key in (
            "ran", "refresh_during_press", "click_delivered",
            "range12_selected", "rolling_window", "preference_saved",
            "no_recorder_reload", "range36_selected", "fixed_36_window",
            "restored_24", "single_card", "main_stable", "card_stable",
            "header_stable", "button_stable", "window_bar_stable",
        )
    ):
        failures.append(
            f"{name}: 12/24/36-hour chart range or stable-DOM regression failed"
        )
    if chart_range_press["error"]:
        failures.append(f"{name}: chart-range press interaction error")
    if not all(
        plan[key] is True
        for key in (
            "ready", "data_changed", "card_stable", "main_stable",
            "layout_control_stable", "auto_control_stable",
            "optimize_control_stable", "costfun_control_stable",
            "max_export_control_stable", "strategy_control_stable",
            "actual_soc_visible", "forecast_soc_visible", "soc_axis_visible",
            "soc_values_valid", "soc_targets_interval_end",
        )
    ):
        failures.append(f"{name}: plan refresh rebuilt more than the graph card or did not refresh")
    if plan["error"]:
        failures.append(f"{name}: battery-plan refresh interaction error")
    if EXPECTED_ENTRYPOINT in {"v051", "v100", "v101", "v110", "v130"} and not all(
        execution_history.get(key) is True
        for key in (
            "ran", "single_card", "compact_rows", "future_rows",
            "wanted_soc_history", "source_bars", "ev_charge_underlay",
            "ev_hold_underlay", "modal_open", "modal_rows",
            "modal_no_filter", "card_stable", "main_stable", "modal_closed",
        )
    ):
        failures.append(
            f"{name}: EMHASS-to-GoodWe history/source UI regression failed: "
            f"{execution_history}"
        )
    if execution_history["error"]:
        failures.append(f"{name}: execution-history interaction error")
    if EXPECTED_ENTRYPOINT in {"v110", "v130"}:
        required_beta_tests = (
            "ran", "initially_hidden", "menu_entry", "opened", "dashboard_hidden", "touch_targets",
            "responsive", "telemetry_main_stable", "telemetry_tests_stable",
            "structural_tests_stable", "structural_open_preserved", "local_only",
            "closed", "dashboard_restored",
        )
        controls = beta_tests.get("controls", {})
        methods = beta_tests.get("methods", {})
        method_keys = (
            "method-native-click", "method-pointerup-direct",
            "method-pointerup-delegated", "method-click-fallback",
            "method-pointerup-dedupe",
        )
        methods_ok = all(
            methods.get(key, {}).get("metrics", {}).get("pointerdown", 0) >= 20
            and methods.get(key, {}).get("metrics", {}).get("pointerup", 0) >= 20
            and methods.get(key, {}).get("metrics", {}).get("actions", 0)
            == (21 if key == "method-click-fallback" else 20)
            and methods.get(key, {}).get("connected") is True
            for key in method_keys
        )
        dedupe_ok = (
            methods.get("method-pointerup-dedupe", {}).get("metrics", {}).get(
                "pointer_actions", 0
            ) == 20
            and methods.get("method-pointerup-dedupe", {}).get("metrics", {}).get(
                "deduped", 0
            ) == 20
            and methods.get("method-click-fallback", {}).get("metrics", {}).get(
                "fallback_actions", 0
            ) == 1
            and methods.get("method-pointerup-direct", {}).get("metrics", {}).get(
                "pointer_actions", 0
            ) == 20
        )
        button_controls = (
            "lit-button", "listener-button", "icon-button", "shadow-button",
            "checkbox-switch", "label-switch",
        )
        repeated_ok = all(
            controls.get(key, {}).get("metrics", {}).get("pointerdown", 0) >= 20
            and controls.get(key, {}).get("metrics", {}).get("pointerup", 0) >= 20
            and controls.get(key, {}).get("metrics", {}).get("click", 0) >= 20
            and controls.get(key, {}).get("metrics", {}).get("actions", 0) == 20
            for key in button_controls
        )
        native_ok = all(
            controls.get(key, {}).get("metrics", {}).get("actions", 0) >= 20
            and controls.get(key, {}).get("connected") is True
            for key in ("native-select", "native-range")
        )
        if (
            not all(beta_tests.get(key) is True for key in required_beta_tests)
            or not methods_ok
            or not dedupe_ok
            or not repeated_ok
            or not native_ok
        ):
            failures.append(
                f"{name}: Beta tests local control laboratory regressed: {beta_tests}"
            )
        if beta_tests["error"]:
            failures.append(f"{name}: Beta tests interaction error")
        required_fallback = (
            "ran", "installed", "operational_fallback", "late_click_deduped",
            "movement_rejected", "cancel_rejected", "menu_opened", "menu_switch",
            "menu_reset", "beta_opened", "beta_raw_control_excluded", "beta_closed",
            "settings_opened", "settings_tab", "settings_closed",
            "chart_touch_targets", "chart_controls_fit", "chart_size_fallback",
            "chart_range_fallback",
            "history_fallback", "history_close_fallback",
        )
        if not all(touch_click_fallback.get(key) is True for key in required_fallback):
            failures.append(
                f"{name}: iOS touch click fallback regressed: {touch_click_fallback}"
            )
        if touch_click_fallback["error"]:
            failures.append(f"{name}: iOS touch click fallback interaction error")
    if (
        language_result["localized"] is not True
        or (not control_architecture and language_result["manual_summary_localized"] is not True)
        or language_result["setpoint_update_localized"] is not True
    ):
        failures.append(f"{name}: Dutch structural render did not localize")
    if language_result["flow_localized"] is not True:
        failures.append(f"{name}: Dutch flow accessibility label did not localize")
    if EXPECTED_ENTRYPOINT in {"v110", "v130"} and language_result["help_localized"] is not True:
        failures.append(f"{name}: Dutch help link did not localize")
    if language_result["main_stable_during_telemetry"] is not True:
        failures.append(f"{name}: Dutch telemetry replaced the main DOM")
    if abs(language_result["idle_delta"] or 0) > 2:
        failures.append(f"{name}: Dutch telemetry moved scroll position")
    if not control_architecture and (
        structural["cards"] < 8 or structural["main_rebuilt"] is not True
    ):
        failures.append(f"{name}: deliberate narrow-layout structural render failed")
    if not control_architecture and (
        structural["menu_open"] is not True or structural["menu_close"] is not True
    ):
        failures.append(f"{name}: controls failed after a structural layout render")
    if structural["error"] and not control_architecture:
        failures.append(f"{name}: post-structure menu interaction error")
    if EXPECTED_ENTRYPOINT in STABLE_ENTRYPOINTS and (
        animation["flowParticleAnimations"] <= 0
        or animation["otherAnimations"] != 0
        or animation["transitions"] != 0
    ):
        failures.append(
            f"{name}: scoped flow motion has {animation['flowParticleAnimations']} particle, "
            f"{animation['otherAnimations']} other animations and "
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
    requested_profile = next(
        (
            argument.split("=", 1)[1]
            for argument in sys.argv[1:]
            if argument.startswith("--profile=")
        ),
        None,
    )
    profiles = [
        profile
        for profile in PROFILES
        if requested_profile is None or profile.name == requested_profile
    ]
    if not profiles:
        raise SystemExit(f"Unknown browser profile: {requested_profile}")
    with static_server() as base_url, sync_playwright() as playwright:
        for profile in profiles:
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
            page.on(
                "pageerror",
                lambda error: page_errors.append(
                    getattr(error, "stack", None) or str(error)
                ),
            )
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
