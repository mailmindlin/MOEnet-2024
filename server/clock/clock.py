import time, abc
from datetime import timedelta
from .timestamp import Timestamp

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

class MonoClock(Clock):
    "Monotonic clock"
    def __new__(cls):
        # pseudo-singleton
        if getattr(cls, 'INSTANCE', None) is None:
            cls.INSTANCE = super().__new__(cls)
        return cls.INSTANCE
    
    def now_ns(self) -> int:
        return time.monotonic_ns()


class WallClock(Clock):
    "Wall clock"
    def __new__(cls):
        # pseudo-singleton
        if getattr(cls, 'INSTANCE', None) is None:
            cls.INSTANCE = super().__new__(cls)
        return cls.INSTANCE
    
    def now_ns(self) -> int:
        return time.time_ns()


class OffsetClock(Clock, abc.ABC):
    def __init__(self, base: Clock) -> None:
        super().__init__()
        self.base = base
    
    @abc.abstractmethod
    def get_offset(self) -> int:
        pass

    def now_ns(self) -> int:
        return self.base.now_ns() + self.get_offset()