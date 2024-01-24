from typing import TYPE_CHECKING, Optional, overload
from functools import total_ordering
from datetime import timedelta

if TYPE_CHECKING:
    # Fix import recursion
    from .clock import Clock

@total_ordering
class Timestamp:
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

    __match_args__ = ('nanos', 'clock')
    
    nanos: int
    clock: Optional['Clock']

    def __init__(self, nanos: int, clock: Optional['Clock'] = None):
        self.nanos = int(nanos)
        self.clock = clock
    
    def as_seconds(self) -> float:
        "Get time in fractional seconds"
        return self.nanos / 1_000_000_000
    
    def as_wpi(self) -> int:
        return self.nanos // 1_000

    def __add__(self, other: timedelta) -> 'Timestamp':
        if isinstance(other, timedelta):
            return self.offset(other)
        return NotImplemented
    def split(self):
        return divmod(self.nanos, 1_000_000_000)
    
    @overload
    def __sub__(self, other: timedelta) -> 'Timestamp': ...
    @overload
    def __sub__(self, other: 'Timestamp') -> timedelta: ...
    def __sub__(self, other):
        if isinstance(other, timedelta):
            return self.offset(-other)
        if isinstance(other, Timestamp):
            if other.clock != self.clock:
                return NotImplemented
            return self.difference(other)
        return NotImplemented
    
    def offset(self, offset: timedelta) -> 'Timestamp':
        return Timestamp(self.nanos - (offset.total_seconds() / 1e9), clock=self.clock)
    
    def offset_ns(self, offset: int) -> 'Timestamp':
        return Timestamp(self.nanos + offset, clock=self.clock)

    def difference(self, other: 'Timestamp') -> timedelta:
        delta_ns = self.nanos - other.nanos
        return timedelta(microseconds=delta_ns / 1e3)
    
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
