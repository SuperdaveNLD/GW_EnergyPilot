#!/usr/bin/env python3
"""Permanent EnergyPilot control-surface browser contract.

This complements the historical presentation matrix with the operational
contract introduced by ep-control-surface: native activation, one service
transaction, backend acknowledgement, stable nodes and native scrolling.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_frontend_stability as stability  # noqa: E402


HARNESS = "/tests/browser/frontend_harness.html?entry=v101"
REPETITIONS = 50


def action_count(page: Page, counter: str) -> int:
    return page.evaluate(
        """
        counter => {
          const panel = window.__epPanel;
          if (counter.startsWith('ws:')) {
            const type = counter.slice(3);
            return window.__epWsCalls.filter(call => call.type === type).length;
          }
          const entityId = panel._entityId(counter);
          return window.__epServiceCalls.filter(
            call => call.data?.entity_id === entityId
          ).length;
        }
        """,
        counter,
    )


def activate(
    page: Page,
    profile: stability.Profile,
    selector: str,
    component: str,
    counter: str,
) -> None:
    before = action_count(page, counter)
    control = stability.shadow(page, selector)
    control.scroll_into_view_if_needed(timeout=5_000)
    if profile.touch:
        control.tap(timeout=5_000)
    else:
        control.click(timeout=5_000)
    page.wait_for_function(
        """
        ([counter, expected]) => {
          const panel = window.__epPanel;
          const count = counter.startsWith('ws:')
            ? window.__epWsCalls.filter(call => call.type === counter.slice(3)).length
            : window.__epServiceCalls.filter(
                call => call.data?.entity_id === panel._entityId(counter)
              ).length;
          return count === expected;
        }
        """,
        arg=[counter, before + 1],
        timeout=5_000,
    )
    page.wait_for_function(
        """
        component => {
          const control = window.__epPanel.shadowRoot.querySelector(component);
          return control && control.phase !== 'pending';
        }
        """,
        arg=component,
        timeout=5_000,
    )


def repeat_buttons(
    page: Page,
    profile: stability.Profile,
    name: str,
    selectors: list[str],
    component: str,
    counter: str | list[str],
) -> dict[str, object]:
    counters = counter if isinstance(counter, list) else [counter]
    before = sum(action_count(page, item) for item in counters)
    page.evaluate(
        """
        ([name, selectors]) => {
          window.__epControlIdentities ||= {};
          window.__epControlIdentities[name] = selectors.map(
            selector => window.__epPanel.shadowRoot.querySelector(selector)
          );
        }
        """,
        [name, selectors],
    )
    # Exercise every rendered button 50 times, not merely each control group.
    # Cycling the selectors also prevents state-selectors from becoming no-ops
    # because their already-confirmed option was clicked twice in succession.
    for index in range(REPETITIONS * len(selectors)):
        position = index % len(selectors)
        activate(
            page,
            profile,
            selectors[position],
            component,
            counters[position % len(counters)],
        )
    after = sum(action_count(page, item) for item in counters)
    state = page.evaluate(
        """
        ([name, selectors, component]) => {
          const root = window.__epPanel.shadowRoot;
          const nodes = selectors.map(selector => root.querySelector(selector));
          return {
            stable: nodes.every((node, index) =>
              node === window.__epControlIdentities[name][index] && node?.isConnected
            ),
            phase: root.querySelector(component)?.phase || null,
            pending: nodes.some(node => node?.dataset.pending === 'true'),
          };
        }
        """,
        [name, selectors, component],
    )
    return {
        "calls": after - before,
        "expected": REPETITIONS * len(selectors),
        "stable": state["stable"],
        "settled": state["phase"] == "acknowledged" and not state["pending"],
    }


def repeat_range(
    page: Page,
    profile: stability.Profile,
    name: str,
    selector: str,
    component: str,
    counter: str,
    values: tuple[int, int],
) -> dict[str, object]:
    before = action_count(page, counter)
    page.evaluate(
        "([name, selector]) => { window.__epControlIdentities[name] = [window.__epPanel.shadowRoot.querySelector(selector)]; }",
        [name, selector],
    )
    for index in range(REPETITIONS):
        expected = values[index % 2]
        control = stability.shadow(page, selector)
        control.scroll_into_view_if_needed(timeout=5_000)
        geometry = control.evaluate(
            """
            (input, value) => {
              const rect = input.getBoundingClientRect();
              const minimum = Number(input.min || 0);
              const maximum = Number(input.max || 100);
              const ratio = Math.max(0, Math.min(1, (Number(value) - minimum) / (maximum - minimum)));
              return {
                x: Math.max(2, Math.min(rect.width - 2, rect.width * ratio)),
                y: Math.max(2, rect.height / 2),
              };
            }
            """,
            expected,
        )
        if profile.touch:
            # Playwright WebKit does not finalize a range `change` for tap() or
            # mouse click in a has_touch context. One trusted native keypress is
            # still one range activation/call; physical slider touch remains an
            # explicit iPhone acceptance item. Buttons retain real tap() runs.
            control.press("ArrowRight" if index % 2 == 0 else "ArrowLeft")
            control.press("Tab")
        else:
            control.click(position=geometry, timeout=5_000)
        try:
            page.wait_for_function(
                """
                ([component, counter, expected]) => {
                  const panel = window.__epPanel;
                  const entityId = panel._entityId(counter);
                  const calls = window.__epServiceCalls.filter(
                    call => call.data?.entity_id === entityId
                  ).length;
                  return calls === expected &&
                    panel.shadowRoot.querySelector(component)?.phase !== 'pending';
                }
                """,
                arg=[component, counter, before + index + 1],
                timeout=5_000,
            )
        except PlaywrightError as error:
            state = page.evaluate(
                """
                ([selector, component, counter]) => {
                  const panel = window.__epPanel;
                  const entityId = panel._entityId(counter);
                  return {
                    value: panel.shadowRoot.querySelector(selector)?.value,
                    phase: panel.shadowRoot.querySelector(component)?.phase,
                    calls: window.__epServiceCalls.filter(
                      call => call.data?.entity_id === entityId
                    ).length,
                  };
                }
                """,
                [selector, component, counter],
            )
            raise RuntimeError(
                f"{name} iteration {index + 1} did not commit: {state}"
            ) from error
    after = action_count(page, counter)
    stable = page.evaluate(
        """
        ([name, selector]) => {
          const node = window.__epPanel.shadowRoot.querySelector(selector);
          return node === window.__epControlIdentities[name][0] && node?.isConnected;
        }
        """,
        [name, selector],
    )
    return {
        "calls": after - before,
        "expected": REPETITIONS,
        "stable": stable,
        "activation": "native-keyboard" if profile.touch else "native-track-click",
    }


def exercise_repetitions(page: Page, profile: stability.Profile) -> dict[str, object]:
    page.evaluate("window.__epResetActionLogs()")
    results: dict[str, object] = {}
    results["battery_actions"] = repeat_buttons(
        page,
        profile,
        "battery_actions",
        [
            '[data-action="max_export"]',
            '[data-action="battery_pause"]',
            '[data-action="max_charge"]',
            '[data-action="resume_auto"]',
        ],
        "ep-battery-actions",
        ["max_export", "battery_pause", "max_charge", "resume_auto"],
    )
    results["automatic_control"] = repeat_buttons(
        page,
        profile,
        "automatic_control",
        ["#auto-toggle"],
        "ep-automatic-control",
        "automatic_control",
    )
    results["emhass_strategy"] = repeat_buttons(
        page,
        profile,
        "emhass_strategy",
        [
            '[data-costfun="cost"]',
            '[data-costfun="profit"]',
            '[data-costfun="self-consumption"]',
        ],
        "ep-emhass-strategy",
        "emhass_cost_function",
    )
    results["battery_strategy"] = repeat_buttons(
        page,
        profile,
        "battery_strategy",
        [
            '[data-ep-v038-profile="mad_steve"]',
            '[data-ep-v038-profile="gold_rush"]',
            '[data-ep-v038-profile="balanced"]',
            '[data-ep-v038-profile="battery_saver"]',
            '[data-ep-v038-profile="custom"]',
        ],
        "ep-battery-strategy",
        "ws:gw_energypilot/battery_saver/set",
    )
    results["optimize"] = repeat_buttons(
        page,
        profile,
        "optimize",
        [".ep-optimize-now"],
        "ep-optimize-action",
        "optimize_now",
    )

    page.evaluate("window.__epSetEntityByKey('automatic_control', 'off')")
    page.wait_for_function(
        "() => !window.__epPanel.shadowRoot.querySelector('.ep-v021-mode-button[data-mode=\"8\"]')?.disabled"
    )
    results["manual_modes"] = repeat_buttons(
        page,
        profile,
        "manual_modes",
        [
            f'.ep-v021-mode-button[data-mode="{mode}"]'
            for mode in range(1, 13)
        ],
        "ep-manual-ems-controls",
        "manual_mode",
    )
    results["manual_power"] = repeat_range(
        page,
        profile,
        "manual_power",
        ".ep-v021-power-slider",
        "ep-manual-ems-controls",
        "manual_power",
        (2400, 3600),
    )

    # The five-profile cycle above deliberately ends on Custom.
    page.wait_for_function(
        "() => !window.__epPanel.shadowRoot.querySelector('.ep-v038-custom')?.hidden"
    )
    results["custom_profile"] = repeat_buttons(
        page,
        profile,
        "custom_profile",
        [".ep-v038-custom-save"],
        "ep-battery-strategy",
        "ws:gw_energypilot/battery_saver/custom_set",
    )
    results["minimum_soc"] = repeat_range(
        page,
        profile,
        "minimum_soc",
        '[data-control-id="profile:minimum-soc"]',
        "ep-battery-strategy",
        "emhass_minimum_soc",
        (10, 20),
    )
    results["maximum_soc"] = repeat_range(
        page,
        profile,
        "maximum_soc",
        '[data-control-id="profile:maximum-soc"]',
        "ep-battery-strategy",
        "emhass_maximum_soc",
        (80, 90),
    )
    return results


def exercise_ordering_and_failures(page: Page, profile: stability.Profile) -> dict[str, object]:
    result: dict[str, object] = {}
    page.evaluate(
        """
        () => {
          window.__epActionDelayMs = 18;
          window.__epQuickActionPublishDelayMs = 180;
          window.__epResetActionLogs();
          window.__epSetEntityByKey('automatic_control', 'on');
          window.__epSetEntityByKey('control_command', 'battery_charge');
          window.__epOrderingNode = window.__epPanel.shadowRoot.querySelector(
            '[data-action="battery_pause"]'
          );
        }
        """
    )
    page.wait_for_timeout(100)
    pause = stability.shadow(page, '[data-action="battery_pause"]')
    if profile.touch:
        pause.tap(timeout=5_000)
    else:
        pause.click(timeout=5_000)
    page.evaluate(
        "window.__epPanel.shadowRoot.querySelector('[data-action=\"battery_pause\"]').click()"
    )
    page.wait_for_timeout(70)
    result["delayed_pending"] = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          const node = root.querySelector('[data-action="battery_pause"]');
          return root.querySelector('ep-battery-actions')?.phase === 'pending' &&
            node === window.__epOrderingNode && node?.disabled &&
            node?.getAttribute('aria-pressed') !== 'true' &&
            window.__epServiceCalls.length === 1;
        }
        """
    )
    page.evaluate("window.__epTelemetryBurst(25, 0)")
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('ep-battery-actions')?.phase === 'acknowledged'",
        timeout=5_000,
    )
    result["delayed_acknowledged"] = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          const selected = [...root.querySelectorAll('.ep-battery-action')].filter(
            node => node.getAttribute('aria-pressed') === 'true'
          );
          return selected.length === 1 && selected[0].dataset.action === 'battery_pause' &&
            selected[0] === window.__epOrderingNode && window.__epServiceCalls.length === 1;
        }
        """
    )

    page.evaluate(
        """
        () => {
          window.__epControlTrace.clear();
          window.__epQuickActionPublishDelayMs = 0;
          window.__epServiceReturnDelayMs = 180;
          window.__epSetEntity(
            window.__epPanel._entityId('emhass_cost_function'),
            'Profit',
            {emhass_costfun: 'profit'}
          );
        }
        """
    )
    page.wait_for_timeout(80)
    page.evaluate("window.__epPanel.shadowRoot.querySelector('[data-costfun=\"cost\"]').click()")
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('[data-costfun=\"cost\"]')?.getAttribute('aria-pressed') === 'true'"
    )
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('ep-emhass-strategy')?.phase === 'acknowledged'",
        timeout=5_000,
    )
    result["backend_before_return"] = page.evaluate(
        """
        () => {
          const trace = window.__epControlTrace.snapshot();
          const publication = trace.findIndex(item => item.type === 'hass-state-publication');
          const callEnd = trace.findIndex(item =>
            item.type === 'servicecall-end' && item.controlId === 'emhass:cost'
          );
          return publication >= 0 && callEnd > publication &&
            window.__epPanel.shadowRoot.querySelector('ep-emhass-strategy')?.phase === 'acknowledged';
        }
        """
    )
    page.evaluate("window.__epServiceReturnDelayMs = 0")

    page.evaluate(
        """
        () => {
          window.__epFailureNode = window.__epPanel.shadowRoot.querySelector('#auto-toggle');
          window.__epFailureNode.focus();
          window.__epRejectNextServiceCall = true;
          window.__epFailureNode.click();
        }
        """
    )
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('ep-automatic-control')?.phase === 'error'"
    )
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.activeElement === window.__epFailureNode"
    )
    result["service_error"] = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          const node = root.querySelector('#auto-toggle');
          return node === window.__epFailureNode && !node.disabled &&
            root.activeElement === node &&
            root.querySelector('ep-automatic-control')?.feedback.includes('Injected service failure');
        }
        """
    )
    before = action_count(page, "automatic_control")
    page.evaluate("window.__epFailureNode.click()")
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('ep-automatic-control')?.phase === 'acknowledged'"
    )
    result["service_recovery"] = (
        action_count(page, "automatic_control") == before + 1
        and page.evaluate("window.__epFailureNode === window.__epPanel.shadowRoot.querySelector('#auto-toggle')")
    )

    page.evaluate(
        """
        () => {
          window.__epWsFailureNode = window.__epPanel.shadowRoot.querySelector(
            '[data-ep-v038-profile="gold_rush"]'
          );
          window.__epRejectNextWsCall = true;
          window.__epWsFailureNode.click();
        }
        """
    )
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('ep-battery-strategy')?.phase === 'error'"
    )
    result["websocket_error"] = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          return window.__epWsFailureNode === root.querySelector(
            '[data-ep-v038-profile="gold_rush"]'
          ) && root.querySelector('ep-battery-strategy')?.feedback.includes(
            'Injected WebSocket failure'
          );
        }
        """
    )
    ws_before = action_count(page, "ws:gw_energypilot/battery_saver/set")
    page.evaluate("window.__epWsFailureNode.click()")
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('ep-battery-strategy')?.phase === 'acknowledged'"
    )
    result["websocket_recovery"] = (
        action_count(page, "ws:gw_energypilot/battery_saver/set") == ws_before + 1
    )

    page.evaluate(
        """
        () => {
          window.__epControlAckTimeoutMs = 160;
          window.__epSuppressNextPublication = true;
          window.__epPanel.shadowRoot.querySelector('[data-action="max_export"]').click();
        }
        """
    )
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('ep-battery-actions')?.phase === 'error'",
        timeout=2_000,
    )
    result["missing_ack_error"] = page.evaluate(
        "() => window.__epPanel.shadowRoot.querySelector('ep-battery-actions')?.feedback.includes('confirmation')"
    )
    page.evaluate("delete window.__epControlAckTimeoutMs")

    page.evaluate(
        """
        () => {
          window.__epSetEntityByKey('automatic_control', 'unknown');
          window.__epSetEntityByKey('control_command', 'unknown');
        }
        """
    )
    page.wait_for_timeout(100)
    result["unknown_safe"] = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          return root.querySelector('#auto-toggle')?.disabled &&
            root.querySelectorAll('.ep-battery-action[aria-pressed="true"]').length === 0;
        }
        """
    )
    page.evaluate(
        """
        () => {
          window.__epSetEntityByKey('automatic_control', 'on');
          window.__epSetEntityByKey('control_command', 'battery_charge');
          window.__epActionDelayMs = 0;
        }
        """
    )
    return result


def exercise_events_scroll_keyboard(page: Page) -> dict[str, object]:
    page.evaluate("window.__epResetActionLogs(); window.__epControlTrace.clear()")
    page.evaluate(
        """
        async () => {
          const root = window.__epPanel.shadowRoot;
          const control = root.querySelector('[data-action="max_charge"]');
          control.dispatchEvent(new PointerEvent('pointerdown', {
            bubbles:true, composed:true, pointerId:91, pointerType:'touch'
          }));
          await window.__epTelemetryBurst(25, 0);
          control.dispatchEvent(new PointerEvent('pointerup', {
            bubbles:true, composed:true, pointerId:91, pointerType:'touch'
          }));
          control.click();
        }
        """
    )
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('ep-battery-actions')?.phase === 'acknowledged'"
    )
    pointer_result = page.evaluate(
        """
        () => {
          const trace = window.__epControlTrace.snapshot();
          const types = trace.map(item => item.type);
          return {
            oneCall: window.__epServiceCalls.length === 1,
            traced: ['pointerdown','pointerup','click','servicecall-start','servicecall-end',
              'hass-state-publication'].every(type => types.includes(type)),
            connected: trace.every(item => item.surfaceConnected !== false),
          };
        }
        """
    )

    page.evaluate(
        """
        () => {
          window.__epResetActionLogs();
          const root = window.__epPanel.shadowRoot;
          const control = root.querySelector('[data-action="battery_pause"]');
          const scroller = window.__epScroller;
          control.dispatchEvent(new PointerEvent('pointerdown', {
            bubbles:true, composed:true, pointerId:92, pointerType:'touch', clientY:500
          }));
          control.dispatchEvent(new PointerEvent('pointermove', {
            bubbles:true, composed:true, pointerId:92, pointerType:'touch', clientY:300
          }));
          scroller.scrollTop = Math.min(scroller.scrollHeight - scroller.clientHeight, scroller.scrollTop + 260);
          control.dispatchEvent(new PointerEvent('pointercancel', {
            bubbles:true, composed:true, pointerId:92, pointerType:'touch', clientY:300
          }));
        }
        """
    )
    page.wait_for_timeout(80)
    scroll_result = page.evaluate(
        """
        () => ({
          noCall: window.__epServiceCalls.length === 0,
          panY: getComputedStyle(window.__epPanel.shadowRoot.querySelector('.ep-control-surface')).touchAction === 'pan-y',
          buttonManipulation: [...window.__epPanel.shadowRoot.querySelectorAll('ep-control-surface button')].every(
            button => getComputedStyle(button).touchAction === 'manipulation'
          ),
        })
        """
    )

    page.evaluate("window.__epResetActionLogs(); window.__epSetEntityByKey('automatic_control', 'on')")
    auto = stability.shadow(page, "#auto-toggle")
    auto.focus()
    auto.press("Enter")
    page.wait_for_function(
        "() => window.__epPanel.shadowRoot.querySelector('ep-automatic-control')?.phase === 'acknowledged'"
    )
    auto.press("Space")
    page.wait_for_function(
        "() => window.__epServiceCalls.length === 2 && window.__epPanel.shadowRoot.querySelector('ep-automatic-control')?.phase === 'acknowledged'"
    )
    keyboard_result = page.evaluate(
        """
        () => ({
          calls: window.__epServiceCalls.length,
          focused: window.__epPanel.shadowRoot.activeElement ===
            window.__epPanel.shadowRoot.querySelector('#auto-toggle'),
        })
        """
    )
    return {"pointer": pointer_result, "scroll": scroll_result, "keyboard": keyboard_result}


def exercise_identity_layout(page: Page, profile: stability.Profile) -> dict[str, object]:
    page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          window.__epPermanentIdentity = {
            root,
            main: root.querySelector('main'),
            surface: root.querySelector('ep-control-surface'),
            card: root.querySelector('.panel-card.controller'),
            controls: [...root.querySelectorAll('ep-control-surface button, ep-control-surface input')],
          };
        }
        """
    )
    page.evaluate("window.__epTelemetryBurst(1000, 0)")
    page.wait_for_timeout(500)
    identity = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          const saved = window.__epPermanentIdentity;
          const controls = [...root.querySelectorAll(
            'ep-control-surface button, ep-control-surface input'
          )];
          return {
            root: saved.root === root,
            main: saved.main === root.querySelector('main'),
            surface: saved.surface === root.querySelector('ep-control-surface') && saved.surface.isConnected,
            card: saved.card === root.querySelector('.panel-card.controller'),
            controls: saved.controls.length === controls.length &&
              controls.every((node, index) => node === saved.controls[index] && node.isConnected),
          };
        }
        """
    )

    page.evaluate(
        """
        () => {
          const panel = window.__epPanel;
          panel.narrow = !panel.narrow;
          window.__epSetLanguage('nl');
          panel.panel = {...(panel.panel || {}), title: 'Control architecture probe'};
        }
        """
    )
    page.wait_for_timeout(300)
    structural = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          const saved = window.__epPermanentIdentity;
          const controls = [...root.querySelectorAll(
            'ep-control-surface button, ep-control-surface input'
          )];
          return {
            main: saved.main === root.querySelector('main'),
            surface: saved.surface === root.querySelector('ep-control-surface'),
            controls: saved.controls.length === controls.length &&
              controls.every((node, index) => node === saved.controls[index]),
            localized:
              root.querySelector('ep-control-surface')?.model?.language === 'nl' &&
              root.querySelector('ep-automatic-control .ep-control-title')
                ?.textContent.trim() === 'Automatische bediening' &&
              /Automatische bediening beheert de omvormer|Handmatig eigenaarschap/.test(
                root.querySelector('ep-manual-ems-controls [data-manual-note]')
                  ?.textContent || ''
              ),
          };
        }
        """
    )

    layout = page.evaluate(
        """
        () => {
          const root = window.__epPanel.shadowRoot;
          const controls = [...root.querySelectorAll(
            'ep-control-surface button, ep-control-surface input'
          )].filter(
            control => control.getClientRects().length
          );
          const rects = controls.map(control => control.getBoundingClientRect());
          const overlaps = [];
          for (let left = 0; left < rects.length; left += 1) {
            for (let right = left + 1; right < rects.length; right += 1) {
              const a = rects[left], b = rects[right];
              const width = Math.min(a.right, b.right) - Math.max(a.left, b.left);
              const height = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
              if (width > 1 && height > 1) overlaps.push([left, right]);
            }
          }
          const surface = root.querySelector('.ep-control-surface');
          return {
            targets: controls.every(control => {
              const rect = control.getBoundingClientRect();
              return rect.width >= 44 && rect.height >= 44;
            }),
            accessibleNames: controls.every(control =>
              Boolean(control.getAttribute('aria-label')?.trim()) ||
              Boolean(control.labels?.[0]?.textContent?.trim()) ||
              Boolean(control.textContent?.trim())
            ),
            overlaps: overlaps.length,
            horizontalFit: surface.scrollWidth <= surface.clientWidth + 1,
            focusVisibleRule: [...root.querySelectorAll('style')].some(
              style => style.textContent.includes('button:focus-visible')
            ),
          };
        }
        """
    )
    # Mobile landscape is loaded in a fresh context by main(). Resizing an
    # already active WebKit page can itself emit ResizeObserver loop warnings,
    # which would make a browser-emulation artifact look like an app error.
    layout["landscape"] = None if profile.mobile else {
        "fit": True,
        "targets": True,
        "overlaps": 0,
    }
    return {"telemetry": identity, "structural": structural, "layout": layout}


def validate(result: dict[str, object]) -> list[str]:
    failures: list[str] = []
    for group, state in result["repetitions"].items():
        if state.get("calls") != state.get("expected"):
            failures.append(f"{group}: {state.get('calls')} calls for {state.get('expected')} activations")
        if not state.get("stable"):
            failures.append(f"{group}: control identity changed")
        if "settled" in state and not state.get("settled"):
            failures.append(f"{group}: state machine did not settle")
    for name, value in result["ordering"].items():
        if value is not True:
            failures.append(f"ordering/{name} failed")
    events = result["events"]
    if not all(events["pointer"].values()):
        failures.append(f"pointer/trace contract failed: {events['pointer']}")
    if not all(events["scroll"].values()):
        failures.append(f"scroll contract failed: {events['scroll']}")
    if events["keyboard"] != {"calls": 2, "focused": True}:
        failures.append(f"keyboard contract failed: {events['keyboard']}")
    identity = result["identity"]
    if not all(identity["telemetry"].values()):
        failures.append(f"1000-update identity failed: {identity['telemetry']}")
    if not all(identity["structural"].values()):
        failures.append(f"structural identity failed: {identity['structural']}")
    layout = identity["layout"]
    landscape = layout["landscape"] or {}
    if (
        not layout["targets"]
        or not layout["accessibleNames"]
        or layout["overlaps"]
        or not all(layout[key] for key in ("horizontalFit", "focusVisibleRule"))
        or not landscape.get("fit")
        or not landscape.get("targets")
        or landscape.get("overlaps")
    ):
        failures.append(f"layout/accessibility failed: {layout}")
    if result["page_errors"]:
        failures.append(f"page errors: {result['page_errors']}")
    if result["console_errors"]:
        failures.append(f"console errors: {result['console_errors']}")
    if result["unknown_ws"]:
        failures.append(f"unknown WebSocket calls: {result['unknown_ws']}")
    return failures


def exercise_profile(page: Page, profile: stability.Profile) -> dict[str, object]:
    page.goto(HARNESS, wait_until="domcontentloaded", timeout=30_000)
    page.evaluate("window.__epReady")
    page.wait_for_function(
        """
        () => Boolean(
          window.__epPanel?.shadowRoot?.querySelector('ep-control-surface')?.model?.profiles?.data &&
          window.__epPanel.shadowRoot.querySelectorAll('ep-control-surface button').length >= 25
        )
        """,
        timeout=10_000,
    )
    page.evaluate("window.__epActionDelayMs = 0")
    result = {
        "profile": profile.name,
        "repetitions": exercise_repetitions(page, profile),
        "ordering": exercise_ordering_and_failures(page, profile),
        "events": exercise_events_scroll_keyboard(page),
        "identity": exercise_identity_layout(page, profile),
        "unknown_ws": page.evaluate("Array.from(window.__epUnknownWsTypes).sort()"),
    }
    return result


def main() -> int:
    report: dict[str, object] = {"profiles": [], "failures": []}
    with stability.static_server() as base_url, sync_playwright() as playwright:
        for profile in stability.PROFILES:
            engine = getattr(playwright, profile.engine)
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
            logo = Path(__file__).resolve().parents[2] / "custom_components/gw_energypilot/frontend/logo.png"
            page.route(
                "**/gw_energypilot_static/logo.png",
                lambda route, _request, asset=logo: route.fulfill(path=str(asset)),
            )
            page_errors: list[str] = []
            console_errors: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            try:
                result = exercise_profile(page, profile)
            except (PlaywrightError, RuntimeError, AssertionError) as error:
                result = {"profile": profile.name, "fatal": str(error)}
            if profile.mobile and "fatal" not in result:
                landscape_context = browser.new_context(
                    base_url=base_url,
                    viewport={"width": profile.height, "height": profile.width},
                    is_mobile=True,
                    has_touch=True,
                    device_scale_factor=2,
                    locale="en-US",
                )
                landscape_page = landscape_context.new_page()
                landscape_page.route(
                    "**/gw_energypilot_static/logo.png",
                    lambda route, _request, asset=logo: route.fulfill(path=str(asset)),
                )
                landscape_page.on(
                    "pageerror", lambda error: page_errors.append(str(error))
                )
                landscape_page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type == "error"
                    else None,
                )
                landscape_page.goto(HARNESS, wait_until="domcontentloaded", timeout=30_000)
                landscape_page.evaluate("window.__epReady")
                landscape_page.wait_for_function(
                    "() => Boolean(window.__epPanel?.shadowRoot?.querySelector('ep-control-surface'))",
                    timeout=10_000,
                )
                result["identity"]["layout"]["landscape"] = landscape_page.evaluate(
                    """
                    () => {
                      const root = window.__epPanel.shadowRoot;
                      const surface = root.querySelector('.ep-control-surface');
                      const controls = [...root.querySelectorAll(
                        'ep-control-surface button, ep-control-surface input'
                      )].filter(control => control.getClientRects().length);
                      const rects = controls.map(control => control.getBoundingClientRect());
                      let overlaps = 0;
                      for (let left = 0; left < rects.length; left += 1) {
                        for (let right = left + 1; right < rects.length; right += 1) {
                          const a = rects[left], b = rects[right];
                          const width = Math.min(a.right, b.right) - Math.max(a.left, b.left);
                          const height = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
                          if (width > 1 && height > 1) overlaps += 1;
                        }
                      }
                      return {
                        fit: surface.scrollWidth <= surface.clientWidth + 1,
                        targets: controls.every(control => {
                          const rect = control.getBoundingClientRect();
                          return rect.width >= 44 && rect.height >= 44;
                        }),
                        overlaps,
                      };
                    }
                    """
                )
                landscape_context.close()
            result["page_errors"] = page_errors
            result["console_errors"] = console_errors
            failures = [f"{profile.name}: {failure}" for failure in validate(result)] \
                if "fatal" not in result else [f"{profile.name}: fatal: {result['fatal']}"]
            report["profiles"].append(result)
            report["failures"].extend(failures)
            context.close()
            browser.close()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["failures"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
