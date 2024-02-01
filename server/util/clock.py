from typing import Union, TYPE_CHECKING
import time, abc
from datetime import timedelta
from .timestamp import Timestamp
from .decorators import Singleton

if TYPE_CHECKING:
	from .timemap import TimeMapper


class Clock(abc.ABC):
	@abc.abstractmethod
	def now_ns(self) -> int:
		"Get time in nanoseconds"
		pass
	
	def now(self) -> 'Timestamp':
		"Get timestamp"
		return Timestamp(self.now_ns(), clock=self)

	__call__ = now
	
	def __add__(self, /, offset: timedelta) -> 'Clock':
		"Apply offset to clock"
		if isinstance(offset, timedelta):
			return self.with_offset(offset)
		return NotImplemented

	def with_offset(self, offset: timedelta) -> 'Clock':
		return FixedOffsetClock(self, offset)

	def from_offset(self, offset: timedelta) -> 'Timestamp':
		# Round correctly
		return self.now() + offset
	
	def close(self):
		pass

class MonoClock(Clock, Singleton):
	"Monotonic clock, wraps `time.monotonic_ns()`"
	def now_ns(self) -> int:
		return time.monotonic_ns()


class WallClock(Clock, Singleton):
	"Wall clock, wraps `time.time_ns()`"
	def now_ns(self) -> int:
		return time.time_ns()


class OffsetClock(Clock, abc.ABC):
	def __init__(self, base: Clock) -> None:
		super().__init__()
		self.base = base

	@property
	def constant_offset(self):
		"Is the offset relative to base constant? Used for optimizations."
		return False
	
	@abc.abstractmethod
	def get_offset_ns(self) -> int:
		"Get offset, in nanoseconds relative to `base`"
		pass

	def get_offset(self) -> timedelta:
		"Get offset relative to `base`"
		return timedelta(microseconds=self.get_offset_ns()/1000)

	def now_ns(self) -> int:
		return self.base.now_ns() + self.get_offset_ns()

class FixedOffsetClock(OffsetClock):
	"A clock with a fixed offset"
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