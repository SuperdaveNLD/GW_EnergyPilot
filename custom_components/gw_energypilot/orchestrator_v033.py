"""GW EnergyPilot v0.33 persistent-plan orchestration layer."""

from __future__ import annotations

import logging

from .orchestrator_v031 import GWEnergyPilotOrchestrator as _BaseOrchestrator

_LOGGER = logging.getLogger(__name__)


class GWEnergyPilotOrchestrator(_BaseOrchestrator):
    """Mirror each successful EMHASS optimization into the plan runtime."""

    def _plan_runtime(self):
        runtime_data = getattr(self.entry, "runtime_data", None)
        return getattr(runtime_data, "plan_runtime", None)

    async def async_optimize(self, reason: str = "manual") -> None:
        """Run the existing solve/publish path, then refresh the persistent plan."""
        await super().async_optimize(reason=reason)
        plan_runtime = self._plan_runtime()
        if plan_runtime is None:
            return
        try:
            await plan_runtime.async_refresh(reason=f"optimization:{reason}")
        except Exception:  # noqa: BLE001 - plan mirroring must not fail a valid solve
            _LOGGER.exception(
                "Unable to refresh persistent EMHASS plan after successful optimization"
            )
