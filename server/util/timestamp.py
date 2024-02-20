from typing import TYPE_CHECKING, overload, Optional, Literal, Union, TypeVar, Generic
from functools import total_ordering
from datetime import timedelta
import warnings

if TYPE_CHECKING:
	from logging import Logger
	# Fix import recursion
	from .clock import Clock
	from .timemap import TimeMap

class TimestampContext:
	log: Optional['Logger']
	incompatible_clock_strategy: Literal[None, 'warn', 'error'] = 'warn'
	unknown_clock_strategy: Literal[None, 'warn', 'error'] = 'warn'

@total_ordering
class Timestamp:
	"""
	Represents a timestamp.

	We use this class over Python's datetime because it:
	 - Has useful methods for WPIlib conversion
	 - Handles multiple clocks
	 - Stores time in integer nanoseconds (compatibility with Java)
	"""

	@classmethod
	def invalid(cls, clock: Optional['Clock'] = None) -> 'Timestamp':
		return cls(0, clock=clock)

	@classmethod
	def from_seconds(cls, seconds: float, clock: Optional['Clock'] = None) -> 'Timestamp':
		return cls.from_nanos(int(seconds * 1_000_000_000 + 0.5), clock)
	
	@classmethod
	def from_micros(cls, micros: int, clock: Optional['Clock'] = None) -> 'Timestamp':
		return cls.from_nanos(int(micros * 1_000 + 0.5), clock)
	
	@classmethod
	def from_wpi(cls, micros: int, clock: Optional['Clock'] = None):
		"From WPIlib time (microseconds)"
		return cls.from_micros(micros, clock)

	@staticmethod
	def from_nanos(nanos: int, clock: Optional['Clock'] = None) -> 'Timestamp':
		return Timestamp(nanos, clock)
	
	@classmethod
	def wrap_wpi(cls, micros: Union['Timestamp', int], clock: Optional['Clock'] = None):
		"Wrap a (possibly integer) argument"
		if isinstance(micros, cls):
			micros.assert_src(clock)
			return micros
		return cls.from_wpi(micros, clock=clock)

	__slots__ = ('nanos', 'clock')
	__match_args__ = ('nanos', 'clock')
	
	nanos: int
	clock: Optional['Clock']

	def __init__(self, nanos: int, clock: Optional['Clock'] = None):
		self.nanos = int(nanos)
		self.clock = clock
	
	@property
	def is_valid(self) -> bool:
		return self.nanos != 0
	
	def as_seconds(self) -> float:
		"Get time in fractional seconds"
		return self.nanos / 1_000_000_000
	
	def as_wpi(self) -> int:
		"Get in wpi-time (integer microseconds)"
		return self.nanos // 1_000

	def __add__(self, other: timedelta) -> 'Timestamp':
		"Apply offset"
		if isinstance(other, timedelta):
			return self.offset(other)
		return NotImplemented

	def split(self):
		"Split into seconds and partial-nanoseconds"
		return divmod(self.nanos, 1_000_000_000)
	
	@overload
	def __sub__(self, /, other: timedelta) -> 'Timestamp':
		"Apply negative offset"
		...
	
	@overload
	def __sub__(self, /, other: 'Timestamp') -> timedelta:
		"Compute the difference between two timestamps"
	def __sub__(self, /, other):
		if isinstance(other, timedelta):
			return self.offset(-other)
		if isinstance(other, Timestamp):
			if other.clock != self.clock:
				return NotImplemented
			return self.difference(other)
		return NotImplemented

	def assert_src(self, clock: Optional['Clock']):
		"Assert source clock"
		pass
	
	def offset(self, offset: timedelta) -> 'Timestamp':
		return Timestamp(self.nanos + (offset.total_seconds() * 1e9), clock=self.clock)
	
	def offset_ns(self, offset: int, clock: Optional['Clock'] = None) -> 'Timestamp':
		return Timestamp(self.nanos + offset, clock=clock or self.clock)

	def difference(self, other: 'Timestamp') -> timedelta:
		delta_ns = self.nanos - other.nanos
		return timedelta(microseconds=delta_ns / 1e3)
	
	def __hash__(self) -> int:
		return hash((self.nanos, self.clock))
	
	def __eq__(self, other: 'Timestamp'):
		if isinstance(other, Timestamp):
			if self.nanos != other.nanos:
				return False
			if self.clock != other.clock:
				return False
			return True
		return NotImplemented
	
	def __lt__(self, other: 'Timestamp'):
		if isinstance(other, Timestamp):
			if self.clock != other.clock:
				return NotImplemented
			return self.nanos < other.nanos
		return NotImplemented
	
	def __gt__(self, other: 'Timestamp'):
		if isinstance(other, Timestamp):
			if self.clock != other.clock:
				return NotImplemented
			return self.nanos > other.nanos
		return NotImplemented
	
	def localize(self, clock: 'Clock', map: Optional['TimeMap'] = None) -> 'Timestamp':
		if self.clock is None:
			warnings.warn('Convert from unknown clock', RuntimeWarning, stacklevel=2)
			return Timestamp(self.nanos, clock)
		if self.clock == clock:
			return self
		
		if map is None:
			from .timemap import TimeMap
			map = TimeMap.default
		
		conv = map.get_conversion(self.clock, clock)
		if conv is None:
			raise RuntimeError('No conversion available')
		return conv.a_to_b(self)

	def __int__(self):
		return self.nanos
	
	def __float__(self):
		#TODO: is this ambiguous
		return self.as_seconds()


T = TypeVar('T')
class Stamped(Generic[T]):
	def __init__(self, value: T, ts: Timestamp):
		self.ts = ts
		self.value = value