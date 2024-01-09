from typing import Callable, List
from enum import IntEnum
from dataclasses import dataclass
from trackers import OffsetTracker, InertialDataIntegrator, ContinuousAngleTracker
import numpy as np
from callbacks import IIOCompleteNotification, BoardState, IIOProvider
from imu_protocol import YPRUpdate, GyroUpdate
from imu_registers import (
	NAVX_CAL_STATUS_IMU_CAL_STATE_MASK,
	NAVX_CAL_STATUS_IMU_CAL_COMPLETE,
)
from ahrs_protocol import AHRSUpdate, AHRSPosUpdate, BoardID
from serial_io import SerialIO
import time
from threading import Thread


class BoardAxis(IntEnum):
	X = 0
	Y = 1
	Z = 2

@dataclass
class BoardYawAxis:
	board_axis: BoardAxis
	"Identifies one of the board axes"
	up: bool
	"true if axis is pointing up (with respect to gravity); false if pointing down."

class SerialDataType(IntEnum):
	PROCESSED_DATA = 0
	"(default):  6 and 9-axis processed data"
	RAW_DATA = 1
	"unprocessed data from each individual sensor"



class AHRSInternal(IIOCompleteNotification):
	def __init__(self, ahrs: 'AHRS') -> None:
		self.ahrs = ahrs
	# IIOCompleteNotification Interface Implementation        */
	def set_ypr(self, ypr_update: YPRUpdate, sensor_timestamp: int):
		# printf("Setting pitch value to %f", ypr_update.pitch)
		self.ahrs._yaw               	= ypr_update.yaw
		self.ahrs._pitch             	= ypr_update.pitch
		self.ahrs._roll              	= ypr_update.roll
		self.ahrs._compass_heading   	= ypr_update.compass_heading
		self.ahrs._last_sensor_timestamp	= sensor_timestamp
	

	def _dispatch_callbacks(self, ahrs_update: AHRSUpdate, sensor_timestamp: int):
		for callback in self.ahrs._callbacks:
			system_timestamp = int(time.monotonic() * 1000)
			callback(system_timestamp, sensor_timestamp, ahrs_update)
		
	def set_AHRSData(self, ahrs_update: AHRSUpdate, sensor_timestamp: int):
		# Update base IMU class variables
		self.ahrs._yaw                    = ahrs_update.yaw
		self.ahrs._pitch                  = ahrs_update.pitch
		self.ahrs._roll                   = ahrs_update.roll
		self.ahrs._compass_heading        = ahrs_update.compass_heading
		self.ahrs._yaw_offset_tracker.update_history(ahrs_update.yaw)

		# Update AHRS class variables

		# 9-axis data
		self.ahrs._fused_heading          = ahrs_update.fused_heading

		# Gravity-corrected linear acceleration (world-frame)
		self.ahrs._world_linear_accel_x   = ahrs_update.linear_accel_x
		self.ahrs._world_linear_accel_y   = ahrs_update.linear_accel_y
		self.ahrs._world_linear_accel_z   = ahrs_update.linear_accel_z

		# Gyro/Accelerometer Die Temperature
		self.ahrs._mpu_temp_c             = ahrs_update.mpu_temp

		# Barometric Pressure/Altitude
		self.ahrs._altitude               = ahrs_update.altitude
		self.ahrs._baro_pressure          = ahrs_update.barometric_pressure

		# Magnetometer Data
		self.ahrs._cal_mag_x              = ahrs_update.cal_mag_x
		self.ahrs._cal_mag_y              = ahrs_update.cal_mag_y
		self.ahrs._cal_mag_z              = ahrs_update.cal_mag_z


		# Status/Motion Detection
		from imu_registers import (
			NAVX_SENSOR_STATUS_MOVING,
			NAVX_SENSOR_STATUS_YAW_STABLE,
			NAVX_SENSOR_STATUS_ALTITUDE_VALID,
			NAVX_CAL_STATUS_MAG_CAL_COMPLETE,
			NAVX_SENSOR_STATUS_MAG_DISTURBANCE
		)
		def sensor_status_test(flag: int):
			return (ahrs_update.sensor_status & flag) != 0
		self.ahrs._is_moving                  = sensor_status_test(NAVX_SENSOR_STATUS_MOVING)
		self.ahrs._is_rotating                = sensor_status_test(NAVX_SENSOR_STATUS_YAW_STABLE)
		self.ahrs._altitude_valid             = sensor_status_test(NAVX_SENSOR_STATUS_ALTITUDE_VALID)
		self.ahrs._is_magnetometer_calibrated = sensor_status_test(NAVX_CAL_STATUS_MAG_CAL_COMPLETE)
		self.ahrs._magnetic_disturbance       = sensor_status_test(NAVX_SENSOR_STATUS_MAG_DISTURBANCE)

		self.ahrs._quaternionW                = ahrs_update.quat_w
		self.ahrs._quaternionX                = ahrs_update.quat_x
		self.ahrs._quaternionY                = ahrs_update.quat_y
		self.ahrs._quaternionZ                = ahrs_update.quat_z

		self.ahrs._last_sensor_timestamp	= sensor_timestamp

		# Notify external data arrival subscribers, if any.
		self._dispatch_callbacks(ahrs_update, sensor_timestamp)

		self.ahrs._UpdateDisplacement(
			self.ahrs._world_linear_accel_x,
			self.ahrs._world_linear_accel_y,
			self.ahrs._update_rate_hz,
			self.ahrs._is_moving
		)

		self.ahrs._yaw_angle_tracker.next_angle(self.ahrs.yaw)

	def set_AHRSPosData(self, ahrs_update: AHRSPosUpdate, sensor_timestamp: int):
		# Update base IMU class variables */
		#printf("Setting pitch to: %f\n", ahrs_update.pitch)
		self.ahrs._yaw                    = ahrs_update.yaw
		self.ahrs._pitch                  = ahrs_update.pitch
		self.ahrs._roll                   = ahrs_update.roll
		self.ahrs._compass_heading        = ahrs_update.compass_heading
		self.ahrs._yaw_offset_tracker.update_history(ahrs_update.yaw)

		# Update AHRS class variables

		# 9-axis data
		self.ahrs._fused_heading          = ahrs_update.fused_heading

		# Gravity-corrected linear acceleration (world-frame)
		self.ahrs._world_linear_accel_x   = ahrs_update.linear_accel_x
		self.ahrs._world_linear_accel_y   = ahrs_update.linear_accel_y
		self.ahrs._world_linear_accel_z   = ahrs_update.linear_accel_z

		# Gyro/Accelerometer Die Temperature
		self.ahrs._mpu_temp_c             = ahrs_update.mpu_temp

		# Barometric Pressure/Altitude
		self.ahrs._altitude               = ahrs_update.altitude
		self.ahrs._baro_pressure          = ahrs_update.barometric_pressure


		# Status/Motion Detection
		from imu_registers import (
			NAVX_SENSOR_STATUS_MOVING,
			NAVX_SENSOR_STATUS_YAW_STABLE,
			NAVX_SENSOR_STATUS_ALTITUDE_VALID,
			NAVX_CAL_STATUS_MAG_CAL_COMPLETE,
			NAVX_SENSOR_STATUS_MAG_DISTURBANCE
		)
		def sensor_status_test(flag: int):
			return (ahrs_update.sensor_status & flag) != 0
		self.ahrs._is_moving                  = sensor_status_test(NAVX_SENSOR_STATUS_MOVING)
		self.ahrs._is_rotating                = sensor_status_test(NAVX_SENSOR_STATUS_YAW_STABLE)
		self.ahrs._altitude_valid             = sensor_status_test(NAVX_SENSOR_STATUS_ALTITUDE_VALID)
		self.ahrs._is_magnetometer_calibrated = sensor_status_test(NAVX_CAL_STATUS_MAG_CAL_COMPLETE)
		self.ahrs._magnetic_disturbance       = sensor_status_test(NAVX_SENSOR_STATUS_MAG_DISTURBANCE)

		self.ahrs._quaternionW                = ahrs_update.quat_w
		self.ahrs._quaternionX                = ahrs_update.quat_x
		self.ahrs._quaternionY                = ahrs_update.quat_y
		self.ahrs._quaternionZ                = ahrs_update.quat_z

		self.ahrs._last_sensor_timestamp	= sensor_timestamp

		# Notify external data arrival subscribers, if any.
		self._dispatch_callbacks(ahrs_update, sensor_timestamp)

		self.ahrs._velocity[0]     = ahrs_update.vel_x
		self.ahrs._velocity[1]     = ahrs_update.vel_y
		self.ahrs._velocity[2]     = ahrs_update.vel_z
		self.ahrs._displacement[0] = ahrs_update.disp_x
		self.ahrs._displacement[1] = ahrs_update.disp_y
		self.ahrs._displacement[2] = ahrs_update.disp_z

		self.ahrs._yaw_angle_tracker.next_angle(self.ahrs._yaw)
		self.ahrs._last_sensor_timestamp	= sensor_timestamp
	
	def set_raw_data(self, raw_data_update: GyroUpdate, sensor_timestamp: int):
		self.ahrs._raw_gyro_x     = raw_data_update.gyro_x
		self.ahrs._raw_gyro_y     = raw_data_update.gyro_y
		self.ahrs._raw_gyro_z     = raw_data_update.gyro_z
		self.ahrs._raw_accel_x    = raw_data_update.accel_x
		self.ahrs._raw_accel_y    = raw_data_update.accel_y
		self.ahrs._raw_accel_z    = raw_data_update.accel_z
		self.ahrs._cal_mag_x      = raw_data_update.mag_x
		self.ahrs._cal_mag_y      = raw_data_update.mag_y
		self.ahrs._cal_mag_z      = raw_data_update.mag_z
		self.ahrs._mpu_temp_c     = raw_data_update.temp_c
		self.ahrs._last_sensor_timestamp	= sensor_timestamp
	
	def set_board_id(self, board_id: BoardID):
		self.ahrs._board_type = board_id.type
		self.ahrs._hw_rev = board_id.hw_rev
		self.ahrs._fw_ver_major = board_id.fw_ver_major
		self.ahrs._fw_ver_minor = board_id.fw_ver_minor
	def set_BoardState(self, board_state: BoardState):
		self.ahrs._update_rate_hz = board_state.update_rate_hz
		self.ahrs._accel_fsr_g = board_state.accel_fsr_g
		self.ahrs._gyro_fsr_dps = board_state.gyro_fsr_dps
		self.ahrs._capability_flags = board_state.capability_flags
		self.ahrs._op_status = board_state.op_status
		self.ahrs._sensor_status = board_state.sensor_status
		self.ahrs._cal_status = board_state.cal_status
		self.ahrs._selftest_status = board_state.selftest_status

	# IBoardCapabilities Interface Implementation        */
	def is_omnimount_supported(self) -> bool:
		from imu_registers import NAVX_CAPABILITY_FLAG_OMNIMOUNT
		return (self.ahrs._capability_flags & NAVX_CAPABILITY_FLAG_OMNIMOUNT) != 0
	def is_board_yaw_reset_supported(self) -> bool:
		from imu_registers import NAVX_CAPABILITY_FLAG_YAW_RESET
		return (self.ahrs._capability_flags & NAVX_CAPABILITY_FLAG_YAW_RESET) != 0
	def is_displacement_supported(self) -> bool:
		from imu_registers import NAVX_CAPABILITY_FLAG_VEL_AND_DISP
		return (self.ahrs._capability_flags & NAVX_CAPABILITY_FLAG_VEL_AND_DISP) != 0
	def is_AHRSPosTimestamp_supported(self) -> bool:
		from imu_registers import NAVX_CAPABILITY_FLAG_AHRSPOS_TS
		return (self.ahrs._capability_flags & NAVX_CAPABILITY_FLAG_AHRSPOS_TS) != 0

YAW_HISTORY_LENGTH = 10
DEFAULT_ACCEL_FSR_G = 2
DEFAULT_GYRO_FSR_DPS = 2000

NavXCallback = Callable[[AHRSUpdate, int, int], None]

def _thread_func(io: IIOProvider):
	io.run()

class AHRS:
	_yaw: float
	_pitch: float
	_roll: float
	_compass_heading: float
	_world_linear_accel_x: float
	_world_linear_accel_y: float
	_world_linear_accel_z: float
	_mpu_temp_c: float
	_fused_heading: float
	_altitude: float
	_baro_pressure: float
	_is_moving: bool
	_is_rotating: bool
	_baro_sensor_temp_c: float
	_altitude_valid: bool
	_is_magnetometer_calibrated: bool
	_magnetic_disturbance: bool
	_quaternionW: float
	_quaternionX: float
	_quaternionY: float
	_quaternionZ: float
	def __init__(self, serial_port_id: str, data_type: SerialDataType = SerialDataType.PROCESSED_DATA, update_rate_hz: int = 60):
		self._ahrs_internal = AHRSInternal(self)
		self.update_rate_hz = update_rate_hz
		# Processed Data
		self._yaw_offset_tracker = OffsetTracker(YAW_HISTORY_LENGTH)
		self._integrator = InertialDataIntegrator()
		self._yaw_angle_tracker = ContinuousAngleTracker()

		self._yaw = 0.0
		self._pitch = 0.0
		self._roll = 0.0
		self._compass_heading = 0.0
		self._world_linear_accel_x = 0.0
		self._world_linear_accel_y = 0.0
		self._world_linear_accel_z = 0.0


		self._mpu_temp_c = 0.0
		self._fused_heading = 0.0
		self._altitude = 0.0
		self._baro_pressure = 0.0
		self._is_moving = False
		self._is_rotating = False
		self._baro_sensor_temp_c = 0.0
		self._altitude_valid = False
		self._is_magnetometer_calibrated = False
		self._magnetic_disturbance = False
		self._quaternionW = 0.0
		self._quaternionX = 0.0
		self._quaternionY = 0.0
		self._quaternionZ = 0.0

		# Integrated Data
		self._velocity = np.zeros(3, dtype=np.float32)
		self._displacement = np.zeros(3, dtype=np.float32)

		# Raw Data
		self._raw_gyro_x = 0.0
		self._raw_gyro_y = 0.0
		self._raw_gyro_z = 0.0
		self._raw_accel_x = 0.0
		self._raw_accel_y = 0.0
		self._raw_accel_z = 0.0
		self._cal_mag_x = 0.0
		self._cal_mag_y = 0.0
		self._cal_mag_z = 0.0

		# Configuration/Status
		update_rate_hz = 0
		self._accel_fsr_g = DEFAULT_ACCEL_FSR_G
		self._gyro_fsr_dps = DEFAULT_GYRO_FSR_DPS
		self._capability_flags = 0
		self._op_status = 0
		self._sensor_status = 0
		self._cal_status = 0
		self._selftest_status = 0
		# Board ID */
		self._board_type = 0
		self._hw_rev = 0
		self._fw_ver_major = 0
		self._fw_ver_minor = 0
		self._last_sensor_timestamp = 0
		self._last_update_time = 0

		self._callbacks: List[NavXCallback] = list()

		processed_data = (data_type == SerialDataType.PROCESSED_DATA)
		self._io: IIOProvider = SerialIO(serial_port_id, update_rate_hz, processed_data, self._ahrs_internal, self._ahrs_internal)
		
		self._thread = Thread(
			target=_thread_func,
			args=(self._io,),
			name="NavX background",
			daemon=True
		)
		self._thread.start()
	
	def register_callback(self, callback: NavXCallback):
		self._callbacks.append(callback)
	
	def dregister_callback(self, callback: NavXCallback):
		self._callbacks.remove(callback)
	
	def close(self):
		self._io.stop()
		self._thread.join()
	
	def __enter__(self):
		return self
	
	def __exit__(self, *args):
		self.close()
	
	def zero_yaw(self):
		if self._ahrs_internal.is_board_yaw_reset_supported():
			self._io.zero_yaw()
		else:
			self._yaw_offset_tracker.set_offset()
	
	@property
	def yaw(self):
		if self._ahrs_internal.is_board_yaw_reset_supported():
			return self._yaw
		else:
			return self._yaw_offset_tracker.apply_offset(self._yaw)

	@property
	def pitch(self):
		return self._pitch
	@property
	def roll(self):
		return self._roll
	@property
	def lin_accel_x(self):
		return self._world_linear_accel_x
	@property
	def lin_accel_y(self):
		return self._world_linear_accel_y
	@property
	def lin_accel_x(self):
		return self._world_linear_accel_z
	
	@property
	def compass_heading(self):
		return self._compass_heading
	
	def is_calibrating(self):
		return not ((self._cal_status & NAVX_CAL_STATUS_IMU_CAL_STATE_MASK) == NAVX_CAL_STATUS_IMU_CAL_COMPLETE)

	def is_connected(self):
		return self._io.is_connected()

	def get_byte_count(self):
		return self._io.get_byte_count()
	def get_update_count(self):
		return self._io.get_update_count()
	def get_last_sensor_timestamp(self):
		return self._last_sensor_timestamp