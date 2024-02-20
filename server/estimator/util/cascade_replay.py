from datetime import timedelta
from logging import Logger
from typing import TypeVar, Generic
from dataclasses import dataclass

from util.timestamp import Timestamp

from .cascade import Tracked, StaticValue
from .types import HasTimestamp
from .replay import ReplayableFilter, ReplayFilter

M = TypeVar('M', bound=HasTimestamp)
S = TypeVar('S')

@dataclass(order=True)
class WrapTimestamp(Generic[M]):
    ts: Timestamp
    inner: Tracked[M]

class CascadingReplayFilter(ReplayFilter[M, S]):
    def observe(self, measurement: Tracked[M] | M):
        if not isinstance(measurement, Tracked):
            measurement = StaticValue(measurement)
        measurement = measurement.refresh()
        
        return super().observe(WrapTimestamp(measurement.value.ts, measurement))
    
    def _inner_observe(self, measurement: WrapTimestamp[M]):
        return super()._inner_observe(measurement.inner.value)
    
    def predict(self, now: Timestamp, _delta: timedelta = None):
        for tracked in list(self._measurement_history):
            tracked: WrapTimestamp[M]
            # Historical measurement was updated
            if (not tracked.inner.is_static) and (not tracked.inner.is_fresh):
                self._measurement_history.remove(tracked)
                tracked.inner = tracked.inner.refresh()
                assert tracked.inner.value.ts == tracked.ts
                self._measurement_queue.push(tracked)
        
        return super().predict(now, _delta)