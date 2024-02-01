from ntcore import _now as wpi_now

from util.timestamp import Timestamp
from util.clock import Clock
from util.decorators import Singleton


class WpiClock(Clock, Singleton):
	"WPI clock (used for datalog, networktables, etc.)"
	def now_ns(self) -> int:
		# wpilib::Now() returns microseconds
		return wpi_now() * 1000

	def now(self) -> Timestamp:
		return Timestamp.from_wpi(wpi_now(), clock=self)