"""Recovery state for the existing Hybrid 3.0 EV reference callback.

No polling, actuator access or persisted state lives here. Unusable data
fails closed immediately; recovery requires distinct reports from BOTH
sources over at least one existing 15-second reference interval.
"""

from dataclasses import dataclass
from datetime import datetime

from .ev_detection import EV_SELF_CONSUMPTION_INTERVAL_SECONDS


@dataclass
class EVReferenceRecovery:
    recovering: bool = False
    last_fault: str | None = None
    pair: tuple[datetime, datetime] | None = None
    first_valid_at: float | None = None
    fresh_pairs: int = 0

    def invalidate(self, reason: str) -> None:
        self.recovering = True
        self.last_fault = reason
        self.pair = None
        self.first_valid_at = None
        self.fresh_pairs = 0

    def ready(self, pair: tuple[datetime, datetime], now: float) -> bool:
        if not self.recovering:
            return True
        if self.pair is None:
            self.first_valid_at = now
            self.fresh_pairs = 1
            self.pair = pair
        elif pair[0] > self.pair[0] and pair[1] > self.pair[1]:
            self.fresh_pairs += 1
            self.pair = pair
        if (self.fresh_pairs >= 2 and self.first_valid_at is not None
                and now - self.first_valid_at >= EV_SELF_CONSUMPTION_INTERVAL_SECONDS):
            self.recovering = False
            return True
        return False
