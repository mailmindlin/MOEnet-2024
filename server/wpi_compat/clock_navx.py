from typing import Literal
from threading import Lock

from navx import AHRS
import wpilib._wpilib

from util.clock import OffsetClock, Clock
from util.timemap import OffsetClockMapper
from typedef.cfg import NavXConfig

def _map_port(port: Literal['usb', 'usb1', 'usb2']) -> wpilib._wpilib.SerialPort.Port:
	match port:
		case 'usb':
			return wpilib._wpilib.SerialPort.Port.kUSB
		case 'usb1':
			return wpilib._wpilib.SerialPort.Port.kUSB1
		case 'usb2':
			return wpilib._wpilib.SerialPort.Port.kUSB2

class NavXClock(OffsetClock):
	"NavX-synchronized clock"
	def __init__(self, clock: Clock, config: NavXConfig) -> None:
		super().__init__(clock)
		port = _map_port(config.port)
		self.navx = AHRS(port, AHRS.SerialDataType.kProcessedData, config.update_rate)
		self._offset_lock = Lock()
		self._offset = 0
		def update_offset(packet, sensor_ts: int, sys_ts: int):
			# Update offset every packet
			with self._offset_lock:
				self._offset = sensor_ts - sys_ts
		self.navx.register_callback(update_offset)
		# TODO: NavX in subprocess?
	
	def get_offset_ns(self) -> int:
		with self._offset_lock:
			offset_ms = self._offset
		# Offset is in ms
		return offset_ms * 1_000_000
	
	def close(self):
		del self.navx

class NavXTimeMapper(OffsetClockMapper):
	def __init__(self, clock: Clock, config: NavXConfig):
		super().__init__(NavXClock(clock, config))
