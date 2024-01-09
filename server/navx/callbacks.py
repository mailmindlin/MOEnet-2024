from abc import ABC
from dataclasses import dataclass
from imu_protocol import YPRUpdate, GyroUpdate
from ahrs_protocol import AHRSUpdate, AHRSPosUpdate, BoardID

class IBoardCapabilities(ABC):
    def is_omnimount_supported(self) -> bool:
        return False
    def is_board_yaw_reset_supported(self) -> bool:
        return False
    def is_displacement_supported(self) -> bool:
        return False
    def is_AHRSPosTimestamp_supported(self) -> bool:
        return False

@dataclass
class BoardState:
    op_status: int
    sensor_status: int
    cal_status: int
    selftest_status: int
    capability_flags: int
    update_rate_hz: int
    accel_fsr_g: int
    gyro_fsr_dps: int

class IIOProvider(ABC):
    def is_connected(self):
        return False
    def get_byte_count(self) -> float:
        return 0.0
    def get_update_count(self) -> float:
        return 0.0
    def set_update_rate_hz(self, update_rate: int):
        pass
    def zero_yaw(self):
        pass
    def zero_displacement(self):
        pass
    def run(self):
        pass
    def stop(self):
        pass

class IIOCompleteNotification(ABC):
    def set_ypr(self, ypr_update: YPRUpdate, sensor_timestamp: int):
        pass
    def set_AHRSData(self, ahrs_update: AHRSUpdate, sensor_timestamp: int):
        pass
    def set_AHRSPosData(self, ahrs_update: AHRSPosUpdate, sensor_timestamp: int):
        pass
    def set_raw_data(self, raw_data_update: GyroUpdate, sensor_timestamp: int):
        pass
    def set_board_id(self, board_id: BoardID):
        pass
    def set_BoardState(self, board_state: BoardState):
        pass