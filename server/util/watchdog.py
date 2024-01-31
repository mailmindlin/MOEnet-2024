from typing import Union, Optional
from datetime import timedelta
import time
from logging import Logger
from .clock import Clock, MonoClock

class Watchdog:
	"Watchdog for loop timing"
	def __init__(self, name: str, *, min: Union[timedelta, float], max: Union[timedelta, float, None] = None, clock: Optional[Clock] = None, log: Optional[Logger] = None, log_overrun: bool = True) -> None:
		self.name = name
		self.min = min if isinstance(min, timedelta) else timedelta(seconds=min)
		self.clock = clock or MonoClock()
		if max is None:
			self.max = self.min * 2
		elif isinstance(max, timedelta):
			self.max = max
		else:
			self.max = timedelta(seconds=max)
		self._log = log
		self._log_overrun = log_overrun

		self._skip = False
		self.ignore_exceeded = not log_overrun
	
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
		elif (delta > self.max) and (not self.ignore_exceeded):
			if self._log is not None:
				self._log.warning('Watchdog %s exceeded period (%s of %s)', self.name, delta, self.max)
			else:
				import sys
				print(f"Warning: Watchdog {self.name} exceeded period", file=sys.stderr)