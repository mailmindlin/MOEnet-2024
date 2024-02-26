from typing import TYPE_CHECKING, Protocol
import depthai as dai
from util.clock import Clock, FixedOffsetClock, WallClock
from util.decorators import Singleton
from util.timemap import TimeMap, DynamicOffsetMapper, OffsetClockMapper
from util.timestamp import Timestamp
if TYPE_CHECKING:
	from datetime import timedelta


class StampedPacket(Protocol):
    def getTimestamp(self) -> 'timedelta': ...
    def getTimestampDevice(self) -> 'timedelta': ...


class DaiClock(Clock, Singleton):
	"Monotonic clock, wraps `time.monotonic_ns()`"
	def now_ns(self) -> int:
		raw: timedelta = dai.Clock.now()
		return int(raw.total_seconds() * 1e9)

class DeviceTimeSync:
	def __init__(self, reference_clock: Clock | None = None) -> None:
		self.reference_clock = reference_clock or WallClock()
		self.dai_clock = DaiClock()
		self.dev_clock = FixedOffsetClock(self.dai_clock, 0)
		self.map = TimeMap(
			DynamicOffsetMapper(self.reference_clock, self.dai_clock),
			OffsetClockMapper(self.dev_clock),
		)
	
	def local_timestamp(self, packet: StampedPacket) -> 'Timestamp':
		"Convert device time to wall time"
		ts_dai = Timestamp.from_seconds(packet.getTimestamp().total_seconds(), self.dai_clock)
		ts_dev = Timestamp.from_seconds(packet.getTimestampDevice().total_seconds(), self.dev_clock)
		now_dai = self.dai_clock.now()
		now_wall = self.reference_clock.now()
		latency = now_dai - ts_dai

		# Update system -> device time
		self.dev_clock.offset = ts_dev.nanos - ts_dai.nanos

		return now_wall - latency

	def wall_to_device(self, wall: Timestamp) -> float:
		"Convert wall time to device time (useful for SpectacularAI)"
		wall.assert_src(self.reference_clock)
		mapper = self.map.get_conversion(self.reference_clock, self.dev_clock)
		dev = mapper.a_to_b(wall)
		return dev.as_seconds()

	def device_to_wall(self, devtime: float) -> 'Timestamp':
		"Convert device time to wall time (useful for SpectacularAI)"
		dev = Timestamp.from_seconds(devtime, self.dev_clock)
		mapper = self.map.get_conversion(self.dev_clock, self.reference_clock)
		wall = mapper.a_to_b(dev)
		return wall.as_seconds()