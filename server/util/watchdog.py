from typing import TYPE_CHECKING, Optional
from datetime import timedelta
import time, warnings

from .clock import Clock, MonoClock
if TYPE_CHECKING:
	from typing_extensions import TypedDict
	import logging
	from .timestamp import Timestamp

	class BlockArgs(TypedDict):
		block: bool | None
		timeout: float | None

class Watchdog:
	"Watchdog for loop timing"
	min: timedelta
	"Minimum time to take"
	max: timedelta
	"Maximum time to take (logs error if exceeded)"

	def __init__(self, name: str, *, min: timedelta | float | None = None, max: timedelta | float | None = None, clock: Clock | None = None, log: Optional['logging.Logger'] = None, log_overrun: bool = True) -> None:
		self.name = name
		if min is None:
			self.min = timedelta(seconds=0)
		elif isinstance(min, timedelta):
			self.min = min
		else:
			self.min = timedelta(seconds=min)
		assert self.min.total_seconds() >= 0
		
		self.clock = clock or MonoClock()
		if max is None:
			self.max = None
		elif isinstance(max, timedelta):
			self.max = max
		else:
			self.max = timedelta(seconds=max)
		
		if (self.max is not None) and self.max < self.min:
			warnings.warn(f"Watchdog '{name}': max < min", RuntimeWarning)
			self.max = self.min
		
		self._log = log
		self._log_overrun = log_overrun

		self._skip = False
		self.ignore_exceeded = not log_overrun
		self.start = None
	
	def elapsed(self) -> timedelta | None:
		if (start := self.start) is not None:
			return self.clock.now() - start
		return None
	
	def remaining(self) -> timedelta | None:
		if (max := self.max) is not None:
			if (elapsed := self.elapsed()) is not None:
				return max - elapsed
			return self.max
		return None
	
	def has_remaining(self):
		if (remaining := self.remaining_seconds()) is not None:
			return remaining > 0
		return True
	
	def remaining_seconds(self) -> float | None:
		if remaining := self.remaining():
			return remaining.total_seconds()
		return None
	
	def block_args(self) -> 'BlockArgs':
		if remaining := self.remaining_seconds():
			if remaining > 0:
				return { 'block': True, 'timeout': remaining }
			else:
				return { 'block': False }
		return {}
	
	def skip(self):
		self._skip = True

	def __enter__(self):
		self._start = self.clock.now()
		return self
	
	def __exit__(self, *args):
		if self._skip:
			return
		
		delta = (self.clock.now() - self._start)
		if delta < self.min:
			time.sleep((self.min - delta).total_seconds())
		elif (self.max is not None) and (delta > self.max) and (not self.ignore_exceeded):
			if self._log is not None:
				self._log.warning('Watchdog %s exceeded period (%s of %s)', self.name, delta, self.max)
			else:
				warnings.warn(f"Watchdog '{self.name}' exceeded period ({delta} of {self.max})")