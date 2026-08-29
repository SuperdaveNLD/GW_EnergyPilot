# PV insight

GW EnergyPilot can combine the existing internal GoodWe PV total with up to four external Home Assistant PV power entities for dashboard insight.

This feature is deliberately read-only:

```text
GoodWe pv_total_power (optional)
Home Assistant external PV power 1..4 (optional)
                    |
                    v
GW EnergyPilot pv_generation_power entity
                    |
                    v
EnergyPilot PV card + live-flow presentation only
```

The combined value is never passed to Automatic Control, the EMS actuator, EMHASS, persistent grid accounting or an optimization forecast.

## Configuration

Open the EnergyPilot dashboard, select the gear and choose **PV**.

- **Include internal GoodWe PV** is enabled by default to preserve the existing dashboard behavior. It consumes the already canonical `pv_total_power` coordinator value; this feature adds no register and does not infer new GoodWe semantics.
- **Include external PV** independently activates all external sources. The four fields are grouped in one panel, disabled/dimmed while off and active while on.
- **External PV source 1–4** are optional entity-search fields. Each entity must publish non-negative instantaneous PV generation with unit `W`, `kW`, `MW` or `mW`.
- Disabling external PV preserves the selected entity IDs but stops following and summing them.
- The same external entity cannot be selected more than once.
- A combined EnergyPilot `pv_generation_power` entity cannot be selected as an input, preventing recursive PV aggregates.

Missing, unavailable, non-numeric, negative or unsupported-unit readings are shown as unavailable and omitted from the current sum. The combined sensor is available when at least one configured source has a valid reading.

Fresh installations default to external PV disabled. For upgrade compatibility, a v0.45 config entry with an already selected external source is treated as enabled until the new master switch is explicitly saved.

EnergyPilot does not guess a sign convention for an external integration. If an external inverter reports generation as a negative value, create a Home Assistant template sensor that converts it to positive generation before selecting it.

## Entity contract

The integration creates one aggregate power entity with stable unique-ID suffix:

```text
pv_generation_power
```

It uses unit `W`, device class `power` and state class `measurement`. Its attributes include:

```text
internal_enabled
internal_power_w
external_enabled
external_power_w
configured_external_sources
available_external_sources
sources
purpose = display_only
```

The `sources` list keeps the configured topology stable and reports the latest normalized value and availability per source. EnergyPilot does not create one duplicate sensor per selected external entity.

## Dashboard behavior

With no external sources configured, the existing GoodWe PV total and PV1–PV4 breakdown remain unchanged.

When external PV is enabled and at least one source is configured, the PV headline and the PV node in the live-flow presentation use the combined total. The PV card shows a source breakdown for GoodWe PV (when enabled) plus the configured external installations.

Ordinary source updates patch the existing dashboard DOM. Enabling/disabling internal or external PV, or changing the configured source list, is treated as a genuine PV topology change and may trigger one structural render after the integration reload.

## Future GoodWe evidence

Additional GoodWe internal-PV information must follow the register evidence policy in `docs/MODBUS.md`. New register addresses, scales or meanings are not inferred by this display feature. Validated future information can refine the internal source through an intentional code and documentation change without changing the external-source or display-only contract.
