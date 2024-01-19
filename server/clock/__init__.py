from typing import Union, Optional, List
import time

from datetime import timedelta
from abc import ABC, abstractmethod

class Clock(ABC):
    @abstractmethod
    def now(self) -> int:
        "Get time in nanoseconds"
        pass

    def __call__(self) -> int:
        "Get time in nanoseconds"
        return self.now()
    
    def __add__(self, offset: timedelta) -> int:
        if isinstance(offset, timedelta):
            return self.from_offset(offset)
        return NotImplemented

    def from_offset(self, offset: timedelta) -> int:
        # Round correctly
        offset_ns = int(offset.total_seconds() * 1e9 + 0.5)
        return self.now() + offset_ns
    
    def close(self):
        pass


class MonoClock(Clock):
    "Monotonic clock"
    def __new__(cls):
        # pseudo-singleton
        if getattr(cls, 'INSTANCE', None) is None:
            cls.INSTANCE = super().__new__(cls)
        return cls.INSTANCE
    
    def now(self) -> int:
        return time.monotonic_ns()


class WallClock(Clock):
    "Monotonic clock"
    def now(self) -> int:
        return time.time_ns()


class OffsetClock(Clock, ABC):
    def __init__(self, base: Clock) -> None:
        super().__init__()
        self.base = base
    
    @abstractmethod
    def get_offset(self) -> int:
        pass

    def now(self) -> int:
        return self.base.now() + self.get_offset()


class TimeMapper(ABC):
    "Identity time mapper"
    clock_a: Clock
    clock_b: Clock

    def __init__(self, clock_a: Clock, clock_b: Clock) -> None:
        super().__init__()
        self.clock_a = clock_a
        self.clock_b = clock_b
    
    @abstractmethod
    def get_offset(self) -> int:
        "Offset, roughtly (b - a)"
        pass
    
    def a_to_b(self, ts_a: int) -> int:
        return ts_a + self.get_offset()
    
    def b_to_a(self, ts_b: int) -> int:
        return ts_b - self.get_offset()
    
    def __neg__(self) -> 'TimeMapper':
        return InverseTimeMapper(self)
    
    def __shr__(self, rhs: 'TimeMapper') -> 'ChainedTimeMapper':
        "Chain TimeMappers"
        if isinstance(rhs, TimeMapper):
            assert self.clock_b == rhs.clock_a
            return ChainedTimeMapper([self, rhs])
        return NotImplemented


class InverseTimeMapper(TimeMapper):
    def __init__(self, parent: TimeMapper):
        super().__init__(parent.clock_b, parent.clock_a)
        self._parent = parent
    
    def get_offset(self) -> int:
        return -self._parent.get_offset()
    
    def a_to_b(self, ts_a: int) -> int:
        return self._parent.b_to_a(ts_a)
    
    def b_to_a(self, ts_b: int) -> int:
        return self._parent.a_to_b(ts_b)

    def __neg__(self) -> 'TimeMapper':
        return self._parent


class ChainedTimeMapper(TimeMapper):
    def __init__(self, steps: List[TimeMapper]) -> None:
        super().__init__(steps[0].clock_a, steps[-1].clock_b)
        self.steps = steps

        # Check that adjacent pairs are contiguous
        for a, b in zip(steps[:-1], steps[1:]):
            assert a.clock_b == b.clock_a
    
    def get_offset(self) -> int:
        offset = 0
        for step in self.steps:
            offset += step.get_offset()
        return offset
    
    def __shr__(self, rhs: 'TimeMapper') -> 'ChainedTimeMapper':
        "Chain TimeMappers"
        if isinstance(rhs, TimeMapper):
            assert self.clock_b == rhs.clock_a
            steps = list(self.steps)
            # Flatten chains
            if isinstance(rhs, ChainedTimeMapper):
                steps.extend(rhs.steps)
            else:
                steps.append(rhs)
            return ChainedTimeMapper(steps)
        return super().__shr__(rhs)


class FixedOffsetMapper(TimeMapper):
    # Try to compute the offset between the monotonic clock and system time
    # We use this to convert timestamps to system time between processes
    def __init__(self, clock_a: Clock, clock_b: Clock) -> None:
        super().__init__(clock_a, clock_b)
        
        # Compute offset once
        ts_a_1 = clock_a.now()
        ts_b = clock_b.now()
        ts_a_2 = clock_a.now()
        ts_a = (ts_a_1 + ts_a_2) // 2
        self.offset_ns = ts_b - ts_a
    
    def get_offset(self):
        return self.offset_ns


class OffsetClockMapper(TimeMapper):
    clock_b: OffsetClock
    def __init__(self, clock: OffsetClock) -> None:
        super().__init__(clock.base, clock)
    
    def get_offset(self) -> int:
        return self.clock_b.get_offset()


class Watchdog:
    def __init__(self, period: Union[timedelta, float], clock: Optional[Clock] = None) -> None:
        self.period = period if isinstance(period, timedelta) else timedelta(seconds=period)
        self.clock = clock or MonoClock()
        self._skip = False
    
    def skip(self):
        self._skip = True

    def __enter__(self):
        self._start = self.clock.now()
        return self
    
    def __exit__(self, *args):
        if self._skip:
            return
        end = self.clock.now()
        delta = timedelta(seconds=(end - self._start)/1e9)
        if delta < self.period:
            time.sleep(delta.total_seconds())
        elif delta > self.period * 2:
            pass