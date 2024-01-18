from threading import Lock
from . import OffsetClock, MonoClock, Clock, OffsetClockMapper
from ..typedef.cfg import NavXConfig
from ..navx.ahrs import AHRS, SerialDataType

class NavXClock(OffsetClock):
    def __init__(self, clock: Clock, config: NavXConfig) -> None:
        super().__init__(clock)
        self.navx = AHRS(config.port, SerialDataType.PROCESSED_DATA, config.update_rate)
        self._offset_lock = Lock()
        self._offset = 0
        def update_offset(packet, sensor_ts: int, sys_ts: int):
            # Update offset every packet
            with self._offset_lock:
                self._offset = sensor_ts - sys_ts
        self.navx.register_callback(update_offset)
        # TODO: NavX in subprocess?
    
    def get_offset(self) -> int:
        with self._offset_lock:
            offset_ms = self._offset
        # Offset is in ms
        return offset_ms * 1_000_000
    
    def close(self):
        self.navx.close()

class NavXTimeMapper(OffsetClockMapper):
    def __init__(self, config: NavXConfig):
        super().__init__(NavXClock(MonoClock(), config))
