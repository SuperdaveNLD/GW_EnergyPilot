# GW EnergyPilot v0.47 Beta

v0.47 turns Custom Battery Saver policy into an editable, transactional workflow and publishes the completed field-tuned managed profiles. It retains the v0.46 stable dashboard, external-PV controls and all existing GoodWe/EMS control semantics.

## Editable Custom battery costs

**Custom / Aangepast** is now a visible choice in both Battery Strategy on the dashboard and **Settings → EMHASS → Battery Saver**. Administrators can edit these five raw EMHASS values:

```text
battery_soc_deficit_cost
battery_soc_surplus_cost
battery_stress_cost
weight_battery_charge
weight_battery_discharge
```

**Save and optimize** validates that every value is finite and non-negative, preserves the established scalar/one-item-list EMHASS shapes, merges only those fields into the complete active EMHASS configuration and immediately runs a fresh optimization/publish transaction.

If the configuration write or first optimization fails, EnergyPilot restores the previous mode, runtime profile state and all nine Battery Saver-owned EMHASS fields. Custom value editing is intentionally limited to one EMHASS battery model; multi-battery installations can still select Custom to release managed-profile ownership without rewriting their values. Minimum and Maximum SOC remain on their existing synchronized Home Assistant number entities.

## Managed-profile field tuning

- Mad-Steve retains the deliberately aggressive 2.25% × dynamic-price-reference charge and discharge weights.
- Gold Rush, Balanced and Battery Saver use 6% per direction. The captured Gold Rush comparison removed the marginal 765 W, 857 W and 426 W one-slot reversals while preserving profitable 15 kW dispatch.
- Gold Rush battery power stress is reduced from 3% to 1% × dynamic price reference. Balanced and Battery Saver retain 8% and 20%.
- Battery charge/discharge efficiency and inverter topology remain installation-owned.

The preserved field baseline is included under `docs/field_evidence/` so later tuning evidence can be compared without rewriting the original capture.

## Shared high-SOC red zone

All four managed profiles now use a 100% hard EMHASS maximum. The range above 95% is a soft economic red zone rather than unavailable capacity. EMHASS applies profile-specific high-SOC dwell factors of 5% / 10% / 25% / 50% × dynamic price reference for Mad-Steve / Gold Rush / Balanced / Battery Saver.

This keeps 100% available when its forecast value exceeds both transaction cost and accumulated dwell cost, while discouraging charging into the last 5% too early or remaining full unnecessarily.

## Frontend and validation

`gw-energy-pilot-v047.js` is a presentation-only release wrapper over the complete v0.46 chain. The active dependency graph uses the fresh `0.47-custom-battery1` cache key so upgraded browser sessions load the Custom editor, typography and policy presentation coherently.

The release regression set covers backend value validation and shapes, configuration preservation and rollback contracts, dashboard and Settings Custom editing, stable main-node identity, larger typography, desktop Chromium and iPad/iPhone WebKit touch behavior.

## Safety and compatibility

v0.47 changes EMHASS Battery Saver policy only after explicit user selection or Custom save. It does not change GoodWe register definitions, Modbus reads/writes, EMS mode or setpoint ordering, Automatic Control decisions, entity unique IDs, device identity, persistent Store keys, plan resilience, PV aggregation or grid accounting.
