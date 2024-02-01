from typing import Union
import time, abc
from datetime import timedelta
from .timestamp import Timestamp
from .decorators import Singleton

class Clock(abc.ABC):
	@abc.abstractmethod
	def now_ns(self) -> int:
		"Get time in nanoseconds"
		pass
	
	def now(self) -> 'Timestamp':
		"Get timestamp"
		return Timestamp(self.now_ns(), clock=self)

	__call__ = now
	
	def __add__(self, offset: timedelta) -> 'Timestamp':
		if isinstance(offset, timedelta):
			return self.from_offset(offset)
		return NotImplemented

	def from_offset(self, offset: timedelta) -> 'Timestamp':
		# Round correctly
		return self.now() + offset
	
	def close(self):
		pass

class MonoClock(Clock, Singleton):
	"Monotonic clock"
	def now_ns(self) -> int:
		return time.monotonic_ns()


class WallClock(Clock, Singleton):
	"Wall clock"
	def now_ns(self) -> int:
		return time.time_ns()


class OffsetClock(Clock, abc.ABC):
	def __init__(self, base: Clock) -> None:
		super().__init__()
		self.base = base

	@property
	def constant_offset(self):
		return False
	
	@abc.abstractmethod
	def get_offset(self) -> int:
		pass

	def now_ns(self) -> int:
		return self.base.now_ns() + self.get_offset_ns()

class FixedOffsetClock(OffsetClock):
	def __init__(self, base: Clock, offset: Union[int, timedelta]) -> None:
		super().__init__(base)
		self.offset = int(offset.total_seconds() * 1e9) if isinstance(offset, timedelta) else offset

	@property
	def constant_offset(self):
		return True
	
	def get_offset_ns(self) -> int:
		return self.offset

	def __hash__(self) -> int:
		return hash((self.base, self.offset))
	
	def __str__(self):
		return f'{type(self).__name__}({self.base} {"+" if self.offset >= 0 else "-"} {abs(self.offset)}ns)'
	
	def __repr__(self):
		return f'{type(self).__name__}({self.base}, {self.offset})'


class WpiClock(Clock, Singleton):
	def __init__(self):
		super().__init__()
		from ntcore import _now
		self._now = _now
	def now(self) -> int:
		# wpilib::Now() returns microseconds
		return self._now() * 1000