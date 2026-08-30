# GW EnergyPilot v0.50 Beta

v0.50 makes the v0.49 soft EV charger regulator phase-aware and adds explicit charger feedback. It is a focused EV configuration and verification release; GoodWe remains a read-only measurement source for this feature.

## Automatic GoodWe phase measurement

- The manual **Measured phase current** Home Assistant entity is removed from normal EV configuration.
- A one-phase charger uses its configured L1, L2 or L3 GoodWe meter current.
- A three-phase charger requires finite L1/L2/L3 telemetry and guards the highest live phase.
- Missing or invalid required phase telemetry resets the sustained condition and causes no charger write.

## Charger control and feedback

- **Charger current-limit control** accepts only a writable Home Assistant `number` entity in amperes.
- **Charger allocated-current feedback** accepts a read-only current `sensor` in amperes, including `sensor.zorro_de_zaptec_laadpaal_toegewezen_laadstroom`.
- After a current-limit command, EnergyPilot waits up to 60 seconds for feedback within 0.25 A of the target. This treats values such as `15.984 A` as confirmation of a `16 A` request and exposes a mismatch when confirmation does not arrive.
- The EV Online field now accepts `binary_sensor` connectivity entities such as `binary_sensor.zorro_de_zaptec_laadpaal_online`.

Where Home Assistant registry relations identify one unambiguous Zaptec installation, EnergyPilot proposes the matching Available-current NumberEntity and allocated-current feedback sensor. Same-device matches are preferred; ambiguous candidates remain a user choice.

## Timing and migration

New or previously unset load-balancing configurations use a 15-minute sustained condition window. Existing explicitly stored windows remain unchanged. Saving the EV settings removes the obsolete manual phase-current option.

The runtime keeps a compatibility path for an already enabled legacy configuration without allocated-current feedback, but a new enabled save requires feedback so successful application can be verified.

## Safety and compatibility

The load balancer never writes a GoodWe register and never invokes Automatic Control or EMHASS. It writes only the selected charger current-limit NumberEntity through Home Assistant `number.set_value`. The feature remains best-effort software coordination and is not a replacement for correctly rated wiring, breakers, charger protection or the main fuse.

No GoodWe register address, data type, sign convention, EMS mode mapping, setpoint magnitude rule, write ordering, entity unique ID, device identifier, accounting store, plan mirror or Battery Saver ownership changes in v0.50.

The active dashboard is `gw-energy-pilot-v050.js` over the complete v0.49 chain. Every active import uses the fresh `0.50-ev1` cache boundary. The release is covered by unit tests plus the desktop Chromium, iPad WebKit and iPhone WebKit stable-DOM/touch matrix; live GoodWe/Zaptec hardware confirmation remains an installation validation step.
