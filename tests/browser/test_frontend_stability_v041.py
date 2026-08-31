#!/usr/bin/env python3
"""Run the shared browser stability matrix against the v0.41 entrypoint."""

from __future__ import annotations

import test_frontend_stability as stability

stability.HARNESS = "/tests/browser/frontend_harness.html?entry=v041"
stability.EXPECTED_ENTRYPOINT = "v041"


def exercise_emhass_settings(page):
    """Load the active settings wrapper and validate its responsive EMHASS view."""
    return page.evaluate(
        """
        async () => {
          await import('/custom_components/gw_energypilot/frontend/gw-energy-pilot-v041-emhass-settings.js?browser-settings=1');
          const panel = window.__epPanel;
          panel.__epV016SettingsOpen = true;
          panel.__epV016SettingsTab = 'emhass';
          panel.__epV016SettingsData = {
            entry_id: 'test_entry',
            entries: [{ entry_id: 'test_entry', title: 'GW15K-ETA-G20', state: 'loaded' }],
            sections: {
              emhass: {
                title: 'EMHASS',
                short_title: 'EMHASS',
                description: 'Connection, orchestration, outputs and runtime price integration.',
                fields: [
                  { key: 'emhass_url', label: 'EMHASS URL', type: 'text', value: 'http://emhass:5000', readonly: false },
                  { key: 'emhass_optimization_interval', label: 'Optimization interval', type: 'select', value: '15', options: [
                    { value: '15', label: '15 minutes' },
                    { value: '30', label: '30 minutes' },
                    { value: '60', label: '60 minutes' },
                  ], readonly: false },
                  { key: 'p_batt_entity', label: 'P_batt output entity', type: 'text', value: 'sensor.p_batt_forecast', readonly: false },
                  { key: 'p_grid_entity', label: 'P_grid output entity', type: 'text', value: 'sensor.p_grid_forecast', readonly: false },
                  { key: 'optim_status_entity', label: 'Optimization status entity', type: 'text', value: 'sensor.optim_status', readonly: false },
                  { key: 'optim_required_state', label: 'Required optimization state', type: 'text', value: 'Optimal', readonly: false },
                  { key: 'use_nordpool_prices', label: 'Use Nord Pool runtime prices', type: 'boolean', value: true, readonly: false },
                  { key: 'buy_price_adder', label: 'Import price adder', type: 'number', value: 0.02, unit: 'EUR/kWh', readonly: false },
                ],
              },
            },
          };
          panel.__epV028Sync = {
            entryId: 'test_entry',
            loading: false,
            applying: false,
            error: null,
            data: {
              entry_id: 'test_entry',
              available: true,
              synchronized: false,
              recommended_options: {},
              changes: [{
                key: 'sensor_power_battery',
                current: 'sensor.old_battery_power',
                required: 'sensor.gw_energypilot_battery_power',
              }],
              warnings: [],
              managed_values: [
                {
                  key: 'sensor_power_battery',
                  current: 'sensor.old_battery_power',
                  required: 'sensor.gw_energypilot_battery_power',
                  synchronized: false,
                },
                {
                  key: 'sensor_power_load_no_var_loads',
                  current: 'sensor.gw_energypilot_total_load_power',
                  required: 'sensor.gw_energypilot_total_load_power',
                  synchronized: true,
                },
                {
                  key: 'continual_publish',
                  current: false,
                  required: false,
                  synchronized: true,
                },
              ],
            },
          };
          panel._queueRender();
          await new Promise((resolve) => setTimeout(resolve, 120));
          const root = panel.shadowRoot;
          const summary = root.querySelector('.ep-v041-emhass-summary');
          const groups = root.querySelectorAll('.ep-v041-emhass-group');
          const rows = root.querySelectorAll('.ep-v041-emhass-sync-row');
          const control = root.querySelector('.ep-v041-emhass-control');
          const stored = control?.textContent || '';
          const syncButton = root.querySelector('.ep-v041-emhass-sync-action');
          const intervalSelect = root.querySelector(
            'select[data-setting-key="emhass_optimization_interval"]'
          );
          const viewportContained = window.__epScroller.scrollWidth <= window.__epScroller.clientWidth + 2;
          const result = {
            summary: Boolean(summary),
            groups: groups.length,
            rows: rows.length,
            storedMismatch: stored.includes('sensor.old_battery_power'),
            synchronizedValue: stored.includes('sensor.gw_energypilot_total_load_power'),
            syncButton: Boolean(syncButton),
            intervalSelect: Boolean(
              intervalSelect && intervalSelect.value === '15' &&
              intervalSelect.options.length === 3
            ),
            viewportContained,
            customMode: false,
            customInputs: 0,
            customSaved: false,
            customTypography: false,
            profileChoices: root.querySelectorAll('.ep-v031-bs-mode').length,
            comparisonRows: root.querySelectorAll('.ep-v031-bs-comparison tbody tr').length,
            chargegasmVisible: [...root.querySelectorAll('.ep-v031-bs-comparison tbody tr')].some(
              row => row.textContent.includes('Chargegasm') &&
                row.textContent.includes('8%') && row.textContent.includes('96%')
            ),
            managedSlidersHidden: getComputedStyle(
              root.querySelector('.ep-v011-soc-controls')
            ).display === 'none',
            customSlidersVisible: false,
          };
          const customButton = root.querySelector('.ep-v031-bs-mode[data-bs-mode="custom"]');
          customButton?.click();
          for (let attempt = 0; attempt < 40; attempt += 1) {
            if (root.querySelector('[data-bs-custom-form]') && !panel.__epV031BSBusy) break;
            await new Promise((resolve) => setTimeout(resolve, 20));
          }
          const customForm = root.querySelector('[data-bs-custom-form]');
          const requested = {
            battery_soc_deficit_cost: 0.011111,
            battery_soc_surplus_cost: 0.012222,
            battery_stress_cost: 0.013333,
            weight_battery_charge: 0.014444,
            weight_battery_discharge: 0.015555,
          };
          for (const [key, value] of Object.entries(requested)) {
            const input = customForm?.querySelector(`[data-bs-custom-value="${key}"]`);
            if (input) input.value = String(value);
          }
          customForm?.requestSubmit();
          for (let attempt = 0; attempt < 50; attempt += 1) {
            if (!panel.__epV031BSBusy && window.__epWsCalls.some(
              call => call.type === 'gw_energypilot/battery_saver/custom_set'
            )) break;
            await new Promise((resolve) => setTimeout(resolve, 20));
          }
          const customCall = [...window.__epWsCalls].reverse().find(
            call => call.type === 'gw_energypilot/battery_saver/custom_set'
          );
          const currentCustom = root.querySelector('[data-bs-custom-form]');
          const modeTitle = root.querySelector('.ep-v031-bs-mode strong');
          const modeCopy = root.querySelector('.ep-v031-bs-mode p');
          result.customMode = Boolean(
            root.querySelector('.ep-v031-bs-mode[data-bs-mode="custom"].active')
          );
          result.customInputs = currentCustom?.querySelectorAll(
            '[data-bs-custom-value]'
          ).length || 0;
          result.customSaved = JSON.stringify(customCall?.values) === JSON.stringify(requested);
          result.customTypography = Boolean(
            parseFloat(getComputedStyle(modeTitle).fontSize) >= 12 &&
            parseFloat(getComputedStyle(modeCopy).fontSize) >= 10
          );
          result.customSlidersVisible = getComputedStyle(
            root.querySelector('.ep-v011-soc-controls')
          ).display !== 'none';
          result.viewportContained =
            window.__epScroller.scrollWidth <= window.__epScroller.clientWidth + 2;
          if (
            !result.summary || result.groups < 3 || result.rows < 4 ||
            !result.storedMismatch || !result.synchronizedValue ||
            !result.syncButton || !result.intervalSelect || !result.viewportContained || !result.customMode ||
            result.customInputs !== 5 || !result.customSaved || !result.customTypography ||
            result.profileChoices !== 6 || result.comparisonRows !== 5 ||
            !result.chargegasmVisible || !result.managedSlidersHidden ||
            !result.customSlidersVisible
          ) {
            throw new Error(`EMHASS settings layout regression: ${JSON.stringify(result)}`);
          }
          panel.__epV016SettingsOpen = false;
          panel.__epV016Draft = {};
          panel._queueRender();
          await new Promise((resolve) => setTimeout(resolve, 120));
          return result;
        }
        """
    )


def exercise_structural_rerender(page):
    """Exercise the EMHASS settings wrapper, then test a structural dashboard render."""
    result = {
        "cards": 0,
        "main_rebuilt": False,
        "menu_open": False,
        "menu_close": False,
        "error": None,
    }
    try:
        exercise_emhass_settings(page)
        page.wait_for_function(
            """
            () => Boolean(
              window.__epPanel.shadowRoot.querySelector('main[data-ep-v041-stable-dom="1"]') &&
              window.__epPanel.shadowRoot.querySelectorAll('[data-ep-card]').length >= 8
            )
            """,
            timeout=10_000,
        )
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
