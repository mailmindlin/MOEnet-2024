import time
from typedef.cfg import NavXConfig
from datetime import timedelta, datetime
class TimeMapper:
    "Identity time mapper"
    def now(self) -> int:
        return time.monotonic_ns()
    
    def from_offset(self, offset: timedelta) -> int:
        offset_ns = offset.total_seconds() * 1e9
        return self.now() + offset_ns
    
    def apply_ns(self, systime: int) -> int:
        return systime
    
    def inverse_ns(self, remote: int) -> int:
        return remote

class IPTimeMapper(TimeMapper):
    # Try to compute the offset between the monotonic clock and system time
    # We use this to convert timestamps to system time between processes
    def __init__(self) -> None:
        super().__init__()
        mono_ns1 = time.monotonic_ns()
        current_ns = time.time_ns()
        mono_ns2 = time.monotonic_ns()
        mono_ns = (mono_ns1 + mono_ns2) // 2
        self.mono_offset = current_ns - mono_ns
    
    def now(self) -> int:
        return super().now() + self.mono_offset
    
    def apply_ns(self, systime: int) -> int:
        return super().apply_ns(systime)

    def inverse_ns(self, remote: int) -> int:
        return super().inverse_ns(remote)

class NavXTimeMapper(TimeMapper):
    def __init__(self, config: NavXConfig) -> None:
        super().__init__()
        from navx.ahrs import AHRS, SerialDataType
        from threading import Lock
        self.navx = AHRS(config.port, SerialDataType.PROCESSED_DATA, 50)
        self._offset_lock = Lock()
        self._offset = 0
        def update_offset(packet, sensor_ts, sys_ts):
            with self._offset_lock:
                self._offset = sensor_ts - sys_ts
        self.navx.register_callback(update_offset)
        # TODO: NavX in subprocess?
    
    def apply_ns(self, systime: int):
        with self._offset_lock:
            offset = self._offset
        
        return super().apply_ns(systime) + offset
    
    def inverse_ns(self, remote: int) -> int:
        with self._offset_lock:
            offset = self._offset
        
        return super().inverse_ns(remote) - offset
