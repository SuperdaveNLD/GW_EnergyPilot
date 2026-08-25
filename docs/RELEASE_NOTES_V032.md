# GW EnergyPilot v0.32 Beta

Release date: **2026-08-25**

## Hotfix: EMHASS settings can be saved again

v0.31 changed the Home Assistant `NumberSelector` step for the import/export price adjustments from `0.001` to `0.0001`. Current Home Assistant validates selector configuration with a minimum numeric step of `0.001`, so opening/saving the EnergyPilot EMHASS settings could fail with:

```text
not a valid value for dictionary value @ data['step']
```

v0.32 restores the Home Assistant selector configuration to the supported `0.001` step while **preserving four-decimal values such as `0.0248`**. In BOX mode Home Assistant uses `step` for spinner/keyboard increments; typed numeric input is not rounded to the step.

The EnergyPilot dashboard input continues to expose a `0.0001` browser increment, so fine-grained tariff adjustments remain convenient to enter.

## Scope

- Fixes saving **Settings → EMHASS** when four-decimal import/export adjustments are configured.
- Preserves existing values such as `0.0248`; no migration or rounding is performed.
- Adds regression coverage for the Home Assistant selector contract and dashboard four-decimal input behavior.
- Adds the v0.32 frontend release wrapper so the dashboard reports the hotfix version.

## Safety / compatibility

- No GoodWe register, Modbus block, controller mode or write ordering changes.
- No EMHASS optimization model or Battery Saver tuning changes.
- No entity IDs, unique IDs or device identifiers change.
- v0.32 is a focused compatibility hotfix on top of v0.31.
