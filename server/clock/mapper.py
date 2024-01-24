from typing import TYPE_CHECKING, List
from abc import ABC, abstractmethod
from .timestamp import Timestamp
if TYPE_CHECKING:
    from .clock import Clock, OffsetClock

class TimeMapper(ABC):
    "Identity time mapper"
    clock_a: 'Clock'
    clock_b: 'Clock'

    def __init__(self, clock_a: 'Clock', clock_b: 'Clock') -> None:
        super().__init__()
        self.clock_a = clock_a
        self.clock_b = clock_b
    
    @abstractmethod
    def get_offset(self) -> int:
        "Offset, roughtly (b - a)"
        pass
    
    def a_to_b(self, ts_a: Timestamp) -> Timestamp:
        return ts_a.offset_ns(self.get_offset())
    
    def b_to_a(self, ts_b: Timestamp) -> Timestamp:
        return ts_b.offset_ns(-self.get_offset())
    
    def __neg__(self) -> 'TimeMapper':
        "Invert"
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
    
    def a_to_b(self, ts_a: 'Timestamp') -> 'Timestamp':
        return self._parent.b_to_a(ts_a)
    
    def b_to_a(self, ts_b: 'Timestamp') -> 'Timestamp':
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
    """
    Try to compute the offset between the monotonic clock and system time
    We use this to convert timestamps to system time between processes
    """

    @staticmethod
    def computed(clock_a: 'Clock', clock_b: 'Clock') -> 'FixedOffsetMapper':
        # Compute offset once
        ts_a_1 = clock_a.now_ns()
        ts_b = clock_b.now_ns()
        ts_a_2 = clock_a.now_ns()
        ts_a = (ts_a_1 + ts_a_2) // 2
        offset_ns = ts_b - ts_a
        return FixedOffsetMapper(clock_a, clock_b, offset_ns)

    def __init__(self, clock_a: 'Clock', clock_b: 'Clock', offset_ns: int) -> None:
        super().__init__(clock_a, clock_b)
        self.offset_ns = offset_ns
    
    def get_offset(self):
        return self.offset_ns


class IdentityTimeMapper(TimeMapper):
    def __init__(self, clock: 'Clock') -> None:
        super().__init__(clock, clock)
    
    def get_offset(self) -> int:
        return 0


class OffsetClockMapper(TimeMapper):
    clock_b: 'OffsetClock'
    def __init__(self, clock: 'OffsetClock') -> None:
        super().__init__(clock.base, clock)
    
    def get_offset(self) -> int:
        return self.clock_b.get_offset()