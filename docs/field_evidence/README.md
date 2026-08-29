# Field evidence

This directory contains user-supplied, immutable field captures used to compare optimizer behavior. These files are evidence snapshots, not executable test fixtures or canonical configuration.

## Gold Rush baseline — 2026-08-29

- File: `gold-rush-baseline-2026-08-29.txt`
- Source: manually launched EMHASS day-ahead optimization
- Profile: standard, unmodified GW EnergyPilot Gold Rush
- Capture horizon: 2026-08-29 15:15 through 2026-08-30 15:00 (Europe/Amsterdam)
- Repository HEAD when archived: `6c13b09f1e222dabee3726f1775d1e5b3d59e413`

Keep this baseline unchanged. Store later tuning runs as separate files so power, SOC trajectory, short reversals and objective results can be compared against the original.
