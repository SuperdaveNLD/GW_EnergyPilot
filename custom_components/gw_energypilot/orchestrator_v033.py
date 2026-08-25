"""GW EnergyPilot v0.33 persistent-plan orchestration layer."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.dispatcher import async_dispatcher_send

from .orchestrator_v031 import GWEnergyPilotOrchestrator as _BaseOrchestrator

_LOGGER = logging.getLogger(__name__)


class GWEnergyPilotOrchestrator(_BaseOrchestrator):
    """Mirror each successful EMHASS optimization into the plan runtime."""

    def __init__(self, hass, entry, coordinator) -> None:
        super().__init__(hass, entry, coordinator)
        self.plan_revision = 0

    def _plan_runtime(self):
        runtime_data = getattr(self.entry, "runtime_data", None)
        return getattr(runtime_data, "plan_runtime", None)

    @property
    def attributes(self) -> dict[str, Any]:
        """Expose plan continuity evidence for support diagnostics."""
        attrs = super().attributes
        plan_runtime = self._plan_runtime()
        attrs["plan_revision"] = self.plan_revision
        if plan_runtime is not None:
            attrs.update(
                {
                    "plan_runtime": dict(plan_runtime.diagnostics),
                    "resolved_p_batt": plan_runtime.current_p_batt(),
                    "resolved_p_grid": plan_runtime.current_p_grid(),
                }
            )
        return attrs

    async def async_optimize(self, reason: str = "manual") -> None:
        """Run the existing solve/publish path, then refresh the persistent plan."""
        await super().async_optimize(reason=reason)
        plan_runtime = self._plan_runtime()
        try:
            if plan_runtime is not None:
                await plan_runtime.async_refresh(reason=f"optimization:{reason}")
        except Exception:  # noqa: BLE001 - plan mirroring must not fail a valid solve
            _LOGGER.exception(
                "Unable to refresh persistent EMHASS plan after successful optimization"
            )
        finally:
            # Every successful EnergyPilot optimization advances one explicit
            # plan revision after the mirror refresh attempt. Existing entities
            # already subscribe to this dispatcher signal, so the frontend gets
            # deterministic freshness evidence without adding another sensor.
            self.plan_revision += 1
            async_dispatcher_send(self.hass, self.signal)
