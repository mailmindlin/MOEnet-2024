from . import TimeMapper, MonoClock, OffsetClock, Clock, OffsetClockMapper
from ntcore import NetworkTableInstance, Event, EventFlags, TimeSyncEventData, _now

class WpiClock(Clock):
    def __new__(cls):
        # pseudo-singleton
        if getattr(cls, 'INSTANCE', None) is None:
            cls.INSTANCE = super().__new__(cls)
        return cls.INSTANCE
    
    def now(self) -> int:
        # wpilib::Now() returns microseconds
        return _now() * 1000


class NetworkTableClock(OffsetClock):
    "Clock that counts NetworkTables server time"
    def __init__(self, nt: NetworkTableInstance) -> None:
        super().__init__(WpiClock())
        self._offset_micros = 0
        self._nt = nt
        self._listener_handle = nt.addTimeSyncListener(True, self._time_sync)
    
    def _time_sync(self, event: Event):
        if not event.is_(EventFlags.kTimeSync):
            return
        data: TimeSyncEventData = event.data
        self._offset_micros = data.serverTimeOffset
    
    def close(self):
        self._nt.removeListener(self._listener_handle)
        return super().close()


class NetworkTableTimeMapper(OffsetClockMapper):
    "Map from WPI-time to NT server-time"
    def __init__(self, nt: NetworkTableInstance):
        super().__init__(NetworkTableClock(nt))