# GW EnergyPilot v0.43 changelog

## Fixed

- Hardened the restart-time EMHASS optimization path so a transiently unavailable GoodWe, EMHASS, Recorder or pricing dependency does not leave the initial post-restart solve as a single one-shot attempt.
- Added bounded startup retries after 15, 30 and 60 seconds when the inherited initial startup optimization fails with a Home Assistant error.
- Prevented a duplicate startup solve when another optimization already completed successfully after the integration finished setting up.
- Preserved the restored `last_success` value as the startup baseline so persisted runtime evidence from before the restart does not incorrectly suppress the intended startup optimization.

## Changed

- Startup-triggered optimization attempts now use `reason=startup` in the existing optimization diagnostics and log path.
- Added `orchestrator_v043.py` as the active bounded restart-resilience layer over the existing v0.33 orchestrator chain.
- Added the v0.43 frontend release wrapper and synchronized manifest/panel version metadata without changing dashboard behavior.
- Extended existing release-chain regressions for the v0.43 wrapper and added dedicated startup-retry regression coverage.

## Safety and compatibility

- No GoodWe register, Modbus read/write block, EMS mode, setpoint, sign convention or write order changed.
- No Automatic Control strategy mapping changed.
- No entity ID, unique ID, config-entry key, device identifier or persistent Store key changed.
- The persistent EMHASS plan remains the restart resilience source while live Home Assistant publication rebuilds.
- The existing live-output warning remains unchanged and clears normally after a successful optimize/publish cycle restores live output.
