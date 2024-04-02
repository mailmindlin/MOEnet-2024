from .clock import OffsetClock
from ..wpi_compat.clock import WpiClock
from .timemap import OffsetClockMapper
from ntcore import NetworkTableInstance, Event, EventFlags, TimeSyncEventData


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

	def get_offset_ns(self) -> int:
		return self._offset_micros * 1_000
	
	def close(self):
		self._nt.removeListener(self._listener_handle)
		return super().close()


class NetworkTableTimeMapper(OffsetClockMapper):
	"Map from WPI-time to NT server-time"
	def __init__(self, nt: NetworkTableInstance):
		super().__init__(NetworkTableClock(nt))
