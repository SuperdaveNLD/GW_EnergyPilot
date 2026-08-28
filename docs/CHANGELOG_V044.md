# GW EnergyPilot v0.44 changelog

## Fixed

- Removed the inherited Optimize-now `_queueRender()` after the asynchronous Home Assistant button service completed.
- Preserved the touched Optimize control and surrounding dashboard DOM through solve, publish and targeted plan refresh.
- Correctly scheduled the first post-restart optimization callback through the active orchestrator chain instead of leaving retry code unreachable.

## Changed

- Added `gw-energy-pilot-v044.js` as the active bounded compatibility layer over v0.43.
- Added in-place Optimize busy/idle, `aria-busy`, orchestrator-status, last-success and error patching with Dutch and English action copy.
- Added `orchestrator_v044.py` above `orchestrator_v033.py` with a 60-second initial background attempt and 15/30/60-second transient retry back-off.
- Skip remaining startup recovery when another EnergyPilot optimization succeeds after setup; preserve the normal periodic schedule after bounded exhaustion.
- Extended unit and real-browser regression coverage for the active v0.44 frontend and orchestrator chains.

## Safety and compatibility

- No GoodWe register, Modbus, EMS actuator, controller decision or EMHASS optimization-objective change.
- No entity identity, config-entry schema, migration or persistent Store contract change.
- No duplicate scheduler or optimizer is introduced; the existing EnergyPilot optimization lock and native schedule remain authoritative.
