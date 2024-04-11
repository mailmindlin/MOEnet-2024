from datetime import timedelta
from dataclasses import dataclass

from util.timestamp import Timestamp

from .cascade import Tracked, StaticValue
from .types import HasTimestamp
from .replay import ReplayFilter
from .interpolated import SortedSequenceAdapter, InterpolatingView

@dataclass(order=True)
class WrapTimestamp[M: HasTimestamp]:
	"Wrap a Tracked so it can be sorted"
	ts: Timestamp
	inner: Tracked[M]

class CascadingReplayFilter[M: HasTimestamp, S: HasTimestamp](ReplayFilter[M, S]):
	def track_state(self, timestamp: Timestamp | None = None) -> Tracked[S]:
		"Track the filter state"
		raise NotImplementedError()
	def observe(self, measurement: Tracked[M] | M):
		if not isinstance(measurement, Tracked):
			measurement = StaticValue(measurement)
		measurement = measurement.refresh()
		
		wrapped = WrapTimestamp(measurement.current.ts, measurement)
		return super().observe(wrapped)
	
	def _inner_observe(self, measurement: WrapTimestamp[M]):
		return super()._inner_observe(measurement.inner.current)
	
	def predict(self, now: Timestamp, delta: timedelta | None = None):
		# Check if any of our historical measurements were updated
		for tracked in list(self._measurement_history):
			tracked: WrapTimestamp[M]
			# Historical measurement was updated
			if (not tracked.inner.is_static) and (not tracked.inner.is_fresh):
				self._measurement_history.remove(tracked)
				tracked.inner = tracked.inner.refresh()
				assert tracked.inner.current.ts == tracked.ts
				self._measurement_queue.push(tracked)
		
		return super().predict(now, delta)