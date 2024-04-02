from datetime import timedelta
from typing import TypeVar, Generic
from dataclasses import dataclass

from util.timestamp import Timestamp

from .cascade import Tracked, StaticValue
from .types import HasTimestamp
from .replay import ReplayFilter

M = TypeVar('M', bound=HasTimestamp)
S = TypeVar('S', bound=HasTimestamp)

@dataclass(order=True)
class WrapTimestamp(Generic[M]):
    "Wrap a Tracked so it can be sorted"
    ts: Timestamp
    inner: Tracked[M]

class CascadingReplayFilter(ReplayFilter[M, S]):
    def observe(self, measurement: Tracked[M] | M):
        if not isinstance(measurement, Tracked):
            measurement = StaticValue(measurement)
        measurement = measurement.refresh()
        
        wrapped = WrapTimestamp(measurement.value.ts, measurement)
        return super().observe(wrapped)
    
    def _inner_observe(self, measurement: WrapTimestamp[M]):
        return super()._inner_observe(measurement.inner.value)
    
    def predict(self, now: Timestamp, delta: timedelta | None = None):
        # Check if any of our historical measurements were updated
        for tracked in list(self._measurement_history):
            tracked: WrapTimestamp[M]
            # Historical measurement was updated
            if (not tracked.inner.is_static) and (not tracked.inner.is_fresh):
                self._measurement_history.remove(tracked)
                tracked.inner = tracked.inner.refresh()
                assert tracked.inner.value.ts == tracked.ts
                self._measurement_queue.push(tracked)
        
        return super().predict(now, delta)