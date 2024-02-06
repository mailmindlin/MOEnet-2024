# This protocol, introduced first with the navX MXP, expands upon the IMU
# protocol by adding the following new functionality:
#
# AHRS Update:  Includes Fused Heading and Altitude Info
# Magnetometer Calibration:  Enables configuration of coefficients from PC
# Board Identity:  Enables retrieval of Board Identification Info
# Fusion Tuning:  Enables configuration of key thresholds/coefficients 
#                 in data fusion algorithms from a remote client
#
# In addition, the navX enable stream command has been extended with a new
# Stream type, in order to enable AHRS Updates.

from typing import Optional
from enum import IntEnum
from dataclasses import dataclass
from imu_protocol import (
    PACKET_START_CHAR,
    verifyChecksum, verifyPrefix,
    decodeProtocolFloat,
    decodeProtocolInt32,
    encodeTermination,
)
import numpy as np
import imu_registers as IMURegisters

BINARY_PACKET_INDICATOR_CHAR = '#'

# AHRS Protocol encodes certain data in binary format, unlike the IMU
# protocol, which encodes all data in ASCII characters.  Thus, the
# packet start and message termination sequences may occur within the
# message content itself.  To support the binary format, the binary
# message has this format:
#
# [start][binary indicator][len][msgid]<MESSAGE>[checksum][terminator
#
# (The binary indicator and len are not present in the ASCII protocol
#
# The [len] does not include the length of the start and binary
# indicator characters, but does include all other message items,
# including the checksum and terminator sequence.

class AHRS_TUNING_VAR_ID(IntEnum):
    UNSPECIFIED = 0
    MOTION_THRESHOLD = 1			# In G
    YAW_STABLE_THRESHOLD = 2		# In Degrees
    MAG_DISTURBANCE_THRESHOLD =3	# Ratio
    SEA_LEVEL_PRESSURE = 4			# Millibars
    MIN_TUNING_VAR_ID = MOTION_THRESHOLD
    MAX_TUNING_VAR_ID = SEA_LEVEL_PRESSURE

class AHRS_DATA_TYPE(IntEnum):
    TUNING_VARIABLE = 0
    MAG_CALIBRATION = 1
    BOARD_IDENTITY = 2

class AHRS_DATA_ACTION(IntEnum):
    DATA_GET = 0
    DATA_SET = 1
    DATA_SET_TO_DEFAULT = 2

DATA_GETSET_SUCCESS	= 0
DATA_GETSET_ERROR	= 1

# AHRS Update Packet - e.g., !a[yaw][pitch][roll][heading][altitude][fusedheading][accelx/y/z][angular rot x/y/z][opstatus][fusionstatus][cr][lf]

MSGID_AHRS_UPDATE = 'a'
AHRS_UPDATE_YAW_VALUE_INDEX = 4 #  Degrees.  Signed Hundredths 
AHRS_UPDATE_ROLL_VALUE_INDEX = 6 #  Degrees.  Signed Hundredths 
AHRS_UPDATE_PITCH_VALUE_INDEX = 8 #  Degrees.  Signed Hundredeths 
AHRS_UPDATE_HEADING_VALUE_INDEX = 10 #  Degrees.  Unsigned Hundredths 
AHRS_UPDATE_ALTITUDE_VALUE_INDEX = 12 #  Meters.   Signed 16:16 
AHRS_UPDATE_FUSED_HEADING_VALUE_INDEX = 16 #  Degrees.  Unsigned Hundredths 
AHRS_UPDATE_LINEAR_ACCEL_X_VALUE_INDEX = 18 #  Inst. G.  Signed Thousandths 
AHRS_UPDATE_LINEAR_ACCEL_Y_VALUE_INDEX = 20 #  Inst. G.  Signed Thousandths 
AHRS_UPDATE_LINEAR_ACCEL_Z_VALUE_INDEX = 22 #  Inst. G.  Signed Thousandths 
AHRS_UPDATE_CAL_MAG_X_VALUE_INDEX = 24 #  Int16 (Device Units) 
AHRS_UPDATE_CAL_MAG_Y_VALUE_INDEX = 26 #  Int16 (Device Units) 
AHRS_UPDATE_CAL_MAG_Z_VALUE_INDEX = 28 #  Int16 (Device Units) 
AHRS_UPDATE_CAL_MAG_NORM_RATIO_VALUE_INDEX = 30 #  Ratio.  Unsigned Hundredths 
AHRS_UPDATE_CAL_MAG_SCALAR_VALUE_INDEX = 32 #  Coefficient. Signed q16:16 
AHRS_UPDATE_MPU_TEMP_VAUE_INDEX = 36 #  Centigrade.  Signed Hundredths 
AHRS_UPDATE_RAW_MAG_X_VALUE_INDEX = 38 #  INT16 (Device Units) 
AHRS_UPDATE_RAW_MAG_Y_VALUE_INDEX = 40 #  INT16 (Device Units) 
AHRS_UPDATE_RAW_MAG_Z_VALUE_INDEX = 42 #  INT16 (Device Units) 
AHRS_UPDATE_QUAT_W_VALUE_INDEX = 44 #  INT16 
AHRS_UPDATE_QUAT_X_VALUE_INDEX = 46 #  INT16 
AHRS_UPDATE_QUAT_Y_VALUE_INDEX = 48 #  INT16 
AHRS_UPDATE_QUAT_Z_VALUE_INDEX = 50 #  INT16 
AHRS_UPDATE_BARO_PRESSURE_VALUE_INDEX = 52 #  millibar.  Signed 16:16 
AHRS_UPDATE_BARO_TEMP_VAUE_INDEX = 56 #  Centigrade.  Signed  Hundredths 
AHRS_UPDATE_OPSTATUS_VALUE_INDEX = 58 #  NAVX_OP_STATUS_XXX 
AHRS_UPDATE_SENSOR_STATUS_VALUE_INDEX = 59 #  NAVX_SENSOR_STATUS_XXX 
AHRS_UPDATE_CAL_STATUS_VALUE_INDEX = 60 #  NAVX_CAL_STATUS_XXX 
AHRS_UPDATE_SELFTEST_STATUS_VALUE_INDEX = 61 #  NAVX_SELFTEST_STATUS_XXX 
AHRS_UPDATE_MESSAGE_CHECKSUM_INDEX =              62
AHRS_UPDATE_MESSAGE_TERMINATOR_INDEX =            64
AHRS_UPDATE_MESSAGE_LENGTH =                      66

# AHRSAndPositioning Update Packet (similar to AHRS, but removes magnetometer and adds velocity/displacement) */

MSGID_AHRSPOS_UPDATE = 'p'
AHRSPOS_UPDATE_YAW_VALUE_INDEX = 4 #  Degrees.  Signed Hundredths 
AHRSPOS_UPDATE_ROLL_VALUE_INDEX = 6 #  Degrees.  Signed Hundredths 
AHRSPOS_UPDATE_PITCH_VALUE_INDEX = 8 #  Degrees.  Signed Hundredeths 
AHRSPOS_UPDATE_HEADING_VALUE_INDEX = 10 #  Degrees.  Unsigned Hundredths 
AHRSPOS_UPDATE_ALTITUDE_VALUE_INDEX = 12 #  Meters.   Signed 16:16 
AHRSPOS_UPDATE_FUSED_HEADING_VALUE_INDEX = 16 #  Degrees.  Unsigned Hundredths 
AHRSPOS_UPDATE_LINEAR_ACCEL_X_VALUE_INDEX = 18 #  Inst. G.  Signed Thousandths 
AHRSPOS_UPDATE_LINEAR_ACCEL_Y_VALUE_INDEX = 20 #  Inst. G.  Signed Thousandths 
AHRSPOS_UPDATE_LINEAR_ACCEL_Z_VALUE_INDEX = 22 #  Inst. G.  Signed Thousandths 
AHRSPOS_UPDATE_VEL_X_VALUE_INDEX = 24 #  Signed 16:16, in meters/sec 
AHRSPOS_UPDATE_VEL_Y_VALUE_INDEX = 28 #  Signed 16:16, in meters/sec 
AHRSPOS_UPDATE_VEL_Z_VALUE_INDEX = 32 #  Signed 16:16, in meters/sec 
AHRSPOS_UPDATE_DISP_X_VALUE_INDEX = 36 #  Signed 16:16, in meters 
AHRSPOS_UPDATE_DISP_Y_VALUE_INDEX = 40 #  Signed 16:16, in meters 
AHRSPOS_UPDATE_DISP_Z_VALUE_INDEX = 44 #  Signed 16:16, in meters 
AHRSPOS_UPDATE_QUAT_W_VALUE_INDEX = 48 #  INT16 
AHRSPOS_UPDATE_QUAT_X_VALUE_INDEX = 50 #  INT16 
AHRSPOS_UPDATE_QUAT_Y_VALUE_INDEX = 52 #  INT16 
AHRSPOS_UPDATE_QUAT_Z_VALUE_INDEX = 54 #  INT16 
AHRSPOS_UPDATE_MPU_TEMP_VAUE_INDEX = 56 #  Centigrade.  Signed Hundredths 
AHRSPOS_UPDATE_OPSTATUS_VALUE_INDEX = 58 #  NAVX_OP_STATUS_XXX 
AHRSPOS_UPDATE_SENSOR_STATUS_VALUE_INDEX = 59 #  NAVX_SENSOR_STATUS_XXX 
AHRSPOS_UPDATE_CAL_STATUS_VALUE_INDEX = 60 #  NAVX_CAL_STATUS_XXX 
AHRSPOS_UPDATE_SELFTEST_STATUS_VALUE_INDEX = 61 #  NAVX_SELFTEST_STATUS_XXX 
AHRSPOS_UPDATE_MESSAGE_CHECKSUM_INDEX =           62
AHRSPOS_UPDATE_MESSAGE_TERMINATOR_INDEX =         64
AHRSPOS_UPDATE_MESSAGE_LENGTH =                   66

# AHRSAndPositioningWithTimestamp Update Packet (similar to AHRSPos, but adds sample timestamp)

MSGID_AHRSPOS_TS_UPDATE = 't'
AHRSPOS_TS_UPDATE_YAW_VALUE_INDEX = 4 #  Signed 16:16.  Signed Hundredths 
AHRSPOS_TS_UPDATE_ROLL_VALUE_INDEX = 8 #  Signed 16:16.  Signed Hundredths 
AHRSPOS_TS_UPDATE_PITCH_VALUE_INDEX = 12 #  Signed 16:16.  Signed Hundredeths 
AHRSPOS_TS_UPDATE_HEADING_VALUE_INDEX = 16 #  Signed 16:16.  Unsigned Hundredths 
AHRSPOS_TS_UPDATE_ALTITUDE_VALUE_INDEX = 20 #  Meters.   Signed 16:16 
AHRSPOS_TS_UPDATE_FUSED_HEADING_VALUE_INDEX = 24 #  Degrees.  Unsigned Hundredths 
AHRSPOS_TS_UPDATE_LINEAR_ACCEL_X_VALUE_INDEX = 28 #  Inst. G.  Signed 16:16 
AHRSPOS_TS_UPDATE_LINEAR_ACCEL_Y_VALUE_INDEX = 32 #  Inst. G.  Signed 16:16 
AHRSPOS_TS_UPDATE_LINEAR_ACCEL_Z_VALUE_INDEX = 36 #  Inst. G.  Signed 16:16 
AHRSPOS_TS_UPDATE_VEL_X_VALUE_INDEX = 40 #  Signed 16:16, in meters/sec 
AHRSPOS_TS_UPDATE_VEL_Y_VALUE_INDEX = 44 #  Signed 16:16, in meters/sec 
AHRSPOS_TS_UPDATE_VEL_Z_VALUE_INDEX = 48 #  Signed 16:16, in meters/sec 
AHRSPOS_TS_UPDATE_DISP_X_VALUE_INDEX = 52 #  Signed 16:16, in meters 
AHRSPOS_TS_UPDATE_DISP_Y_VALUE_INDEX = 56 #  Signed 16:16, in meters 
AHRSPOS_TS_UPDATE_DISP_Z_VALUE_INDEX = 60 #  Signed 16:16, in meters 
AHRSPOS_TS_UPDATE_QUAT_W_VALUE_INDEX = 64 #  Signed 16:16 
AHRSPOS_TS_UPDATE_QUAT_X_VALUE_INDEX = 68 #  Signed 16:16 
AHRSPOS_TS_UPDATE_QUAT_Y_VALUE_INDEX = 72 #  Signed 16:16 
AHRSPOS_TS_UPDATE_QUAT_Z_VALUE_INDEX = 76 #  Signed 16:16 
AHRSPOS_TS_UPDATE_MPU_TEMP_VAUE_INDEX = 80 #  Centigrade.  Signed Hundredths 
AHRSPOS_TS_UPDATE_OPSTATUS_VALUE_INDEX = 82 #  NAVX_OP_STATUS_XXX 
AHRSPOS_TS_UPDATE_SENSOR_STATUS_VALUE_INDEX = 83 #  NAVX_SENSOR_STATUS_XXX 
AHRSPOS_TS_UPDATE_CAL_STATUS_VALUE_INDEX = 84 #  NAVX_CAL_STATUS_XXX 
AHRSPOS_TS_UPDATE_SELFTEST_STATUS_VALUE_INDEX = 85 #  NAVX_SELFTEST_STATUS_XXX 
AHRSPOS_TS_UPDATE_TIMESTAMP_INDEX = 86 #  UINT32 Timestamp, in milliseconds 
AHRSPOS_TS_UPDATE_MESSAGE_CHECKSUM_INDEX =        90
AHRSPOS_TS_UPDATE_MESSAGE_TERMINATOR_INDEX =      92
AHRSPOS_TS_UPDATE_MESSAGE_LENGTH =                94

# Data Get Request:  Tuning Variable, Mag Cal, Board Identity (Response message depends upon request type)
MSGID_DATA_REQUEST = 'D'
DATA_REQUEST_DATATYPE_VALUE_INDEX =               4
DATA_REQUEST_VARIABLEID_VALUE_INDEX =             5
DATA_REQUEST_CHECKSUM_INDEX =                     6
DATA_REQUEST_TERMINATOR_INDEX =                   8
DATA_REQUEST_MESSAGE_LENGTH =                     10

# Data Set Response Packet (in response to MagCal SET and Tuning SET commands.
MSGID_DATA_SET_RESPONSE = 'v'
DATA_SET_RESPONSE_DATATYPE_VALUE_INDEX =          4
DATA_SET_RESPONSE_VARID_VALUE_INDEX =             5
DATA_SET_RESPONSE_STATUS_VALUE_INDEX =            6
DATA_SET_RESPONSE_MESSAGE_CHECKSUM_INDEX =        7
DATA_SET_RESPONSE_MESSAGE_TERMINATOR_INDEX =      9
DATA_SET_RESPONSE_MESSAGE_LENGTH =                11

# Magnetometer Calibration Packet
# This message may be used to SET (store) a new calibration into the navX board, or may be used
# to retrieve the current calibration data from the navX board.
MSGID_MAG_CAL_CMD = 'M'
MAG_CAL_DATA_ACTION_VALUE_INDEX =                 4
MAG_X_BIAS_VALUE_INDEX = 5 #  signed short 
MAG_Y_BIAS_VALUE_INDEX =                          7
MAG_Z_BIAS_VALUE_INDEX =                          9
MAG_XFORM_1_1_VALUE_INDEX = 11 #  signed 16:16 
MAG_XFORM_1_2_VALUE_INDEX =                       15
MAG_XFORM_1_3_VALUE_INDEX =                       19
MAG_XFORM_2_1_VALUE_INDEX =                       23
MAG_XFORM_2_2_VALUE_INDEX =                       27
MAG_XFORM_2_3_VALUE_INDEX =                       31
MAG_XFORM_3_1_VALUE_INDEX =                       35
MAG_XFORM_3_2_VALUE_INDEX =                       39
MAG_XFORM_3_3_VALUE_INDEX =                       43
MAG_CAL_EARTH_MAG_FIELD_NORM_VALUE_INDEX =        47
MAG_CAL_CMD_MESSAGE_CHECKSUM_INDEX =              51
MAG_CAL_CMD_MESSAGE_TERMINATOR_INDEX =            53
MAG_CAL_CMD_MESSAGE_LENGTH =                      55

# Tuning Variable Packet
# This message may be used to SET (modify) a tuning variable into the navX board,
# or to retrieve a current tuning variable from the navX board.
MSGID_FUSION_TUNING_CMD = 'T'
FUSION_TUNING_DATA_ACTION_VALUE_INDEX =           4
FUSION_TUNING_CMD_VAR_ID_VALUE_INDEX =            5
FUSION_TUNING_CMD_VAR_VALUE_INDEX =               6
FUSION_TUNING_CMD_MESSAGE_CHECKSUM_INDEX =        10
FUSION_TUNING_CMD_MESSAGE_TERMINATOR_INDEX =      12
FUSION_TUNING_CMD_MESSAGE_LENGTH =                14

# Board Identity Response Packet
# Sent in response to a Data Get (Board ID) message
MSGID_BOARD_IDENTITY_RESPONSE = 'i'
BOARD_IDENTITY_BOARDTYPE_VALUE_INDEX =            4
BOARD_IDENTITY_HWREV_VALUE_INDEX =                5
BOARD_IDENTITY_FW_VER_MAJOR =                     6
BOARD_IDENTITY_FW_VER_MINOR =                     7
BOARD_IDENTITY_FW_VER_REVISION_VALUE_INDEX =      8
BOARD_IDENTITY_UNIQUE_ID_0 =                      10
BOARD_IDENTITY_UNIQUE_ID_1 =                      11
BOARD_IDENTITY_UNIQUE_ID_2 =                      12
BOARD_IDENTITY_UNIQUE_ID_3 =                      13
BOARD_IDENTITY_UNIQUE_ID_4 =                      14
BOARD_IDENTITY_UNIQUE_ID_5 =                      15
BOARD_IDENTITY_UNIQUE_ID_6 =                      16
BOARD_IDENTITY_UNIQUE_ID_7 =                      17
BOARD_IDENTITY_UNIQUE_ID_8 =                      18
BOARD_IDENTITY_UNIQUE_ID_9 =                      19
BOARD_IDENTITY_UNIQUE_ID_10 =                     20
BOARD_IDENTITY_UNIQUE_ID_11 =                     21
BOARD_IDENTITY_RESPONSE_CHECKSUM_INDEX =          22
BOARD_IDENTITY_RESPONSE_TERMINATOR_INDEX =        24
BOARD_IDENTITY_RESPONSE_MESSAGE_LENGTH =          26

AHRS_PROTOCOL_MAX_MESSAGE_LENGTH = AHRS_UPDATE_MESSAGE_LENGTH

def pfxBin(len: int, msgid: int):
    return [
        PACKET_START_CHAR,
        BINARY_PACKET_INDICATOR_CHAR,
        len - 2,
        msgid,
    ]

def verifyPrefixBin(buffer: bytes, len: int, msgid: int) -> bool:
    return verifyPrefix(buffer, len, pfxBin(len, msgid), len - 4)

@dataclass
class AHRSUpdateBase:
    yaw: float
    pitch: float
    roll: float
    compass_heading: float
    altitude: float
    fused_heading: float
    linear_accel_x: float
    linear_accel_y: float
    linear_accel_z: float
    mpu_temp: float
    quat_w: float
    quat_x: float
    quat_y: float
    quat_z: float
    barometric_pressure: float
    baro_temp: float
    op_status: int
    sensor_status: int
    cal_status: int
    selftest_status: int

class AHRSUpdate(AHRSUpdateBase):
    cal_mag_x: int
    cal_mag_y: int
    cal_mag_z: int
    mag_field_norm_ratio: float
    mag_field_norm_scalar: float
    raw_mag_x: int
    raw_mag_y: int
    raw_mag_z: int

    def encode(self, protocol_buffer: bytearray) -> int:
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
        protocol_buffer[2] = AHRS_UPDATE_MESSAGE_LENGTH - 2
        protocol_buffer[3] = MSGID_AHRS_UPDATE
        # data
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.yaw, protocol_buffer, AHRS_UPDATE_YAW_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.pitch, protocol_buffer, AHRS_UPDATE_PITCH_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.roll, protocol_buffer, AHRS_UPDATE_ROLL_VALUE_INDEX)
        IMURegisters.encodeProtocolUnsignedHundredthsFloat(self.compass_heading, protocol_buffer, AHRS_UPDATE_HEADING_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.altitude,protocol_buffer, AHRS_UPDATE_ALTITUDE_VALUE_INDEX)
        IMURegisters.encodeProtocolUnsignedHundredthsFloat(self.fused_heading, protocol_buffer, AHRS_UPDATE_FUSED_HEADING_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedThousandthsFloat(self.linear_accel_x,protocol_buffer, AHRS_UPDATE_LINEAR_ACCEL_X_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedThousandthsFloat(self.linear_accel_y,protocol_buffer, AHRS_UPDATE_LINEAR_ACCEL_Y_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedThousandthsFloat(self.linear_accel_z,protocol_buffer, AHRS_UPDATE_LINEAR_ACCEL_Z_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.cal_mag_x, protocol_buffer, AHRS_UPDATE_CAL_MAG_X_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.cal_mag_y, protocol_buffer, AHRS_UPDATE_CAL_MAG_Y_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.cal_mag_z, protocol_buffer, AHRS_UPDATE_CAL_MAG_Z_VALUE_INDEX)
        IMURegisters.encodeProtocolUnsignedHundredthsFloat(self.mag_norm_ratio, protocol_buffer, AHRS_UPDATE_CAL_MAG_NORM_RATIO_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.mag_norm_scalar, protocol_buffer, AHRS_UPDATE_CAL_MAG_SCALAR_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.mpu_temp_c, protocol_buffer, AHRS_UPDATE_MPU_TEMP_VAUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.raw_mag_x, protocol_buffer, AHRS_UPDATE_RAW_MAG_X_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.raw_mag_y, protocol_buffer, AHRS_UPDATE_RAW_MAG_Y_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.raw_mag_z, protocol_buffer, AHRS_UPDATE_RAW_MAG_Z_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.quat_w, protocol_buffer, AHRS_UPDATE_QUAT_W_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.quat_x, protocol_buffer, AHRS_UPDATE_QUAT_X_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.quat_y, protocol_buffer, AHRS_UPDATE_QUAT_Y_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.quat_z, protocol_buffer, AHRS_UPDATE_QUAT_Z_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.baro_pressure, protocol_buffer, AHRS_UPDATE_BARO_PRESSURE_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.baro_temp_c, protocol_buffer, AHRS_UPDATE_BARO_TEMP_VAUE_INDEX)

        protocol_buffer[AHRS_UPDATE_OPSTATUS_VALUE_INDEX] = self.op_status
        protocol_buffer[AHRS_UPDATE_SENSOR_STATUS_VALUE_INDEX] = self.sensor_status
        protocol_buffer[AHRS_UPDATE_CAL_STATUS_VALUE_INDEX] = self.cal_status
        protocol_buffer[AHRS_UPDATE_SELFTEST_STATUS_VALUE_INDEX] = self.selftest_status
        # Footer
        encodeTermination( protocol_buffer, AHRS_UPDATE_MESSAGE_LENGTH, AHRS_UPDATE_MESSAGE_LENGTH - 4 )
        return AHRS_UPDATE_MESSAGE_LENGTH
    def decode(self, buffer: bytes) -> Optional[int]:
        if not verifyPrefixBin(buffer, AHRS_UPDATE_MESSAGE_LENGTH, MSGID_AHRS_UPDATE, AHRS_UPDATE_MESSAGE_CHECKSUM_INDEX):
            return None

        self.yaw = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRS_UPDATE_YAW_VALUE_INDEX)
        self.pitch = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRS_UPDATE_PITCH_VALUE_INDEX)
        self.roll = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRS_UPDATE_ROLL_VALUE_INDEX)
        self.compass_heading = IMURegisters.decodeProtocolUnsignedHundredthsFloat(buffer, AHRS_UPDATE_HEADING_VALUE_INDEX)
        self.altitude = IMURegisters.decodeProtocol1616Float(buffer, AHRS_UPDATE_ALTITUDE_VALUE_INDEX)
        self.fused_heading = IMURegisters.decodeProtocolUnsignedHundredthsFloat(buffer, AHRS_UPDATE_FUSED_HEADING_VALUE_INDEX)
        self.linear_accel_x = IMURegisters.decodeProtocolSignedThousandthsFloat(buffer, AHRS_UPDATE_LINEAR_ACCEL_X_VALUE_INDEX)
        self.linear_accel_y = IMURegisters.decodeProtocolSignedThousandthsFloat(buffer, AHRS_UPDATE_LINEAR_ACCEL_Y_VALUE_INDEX)
        self.linear_accel_z = IMURegisters.decodeProtocolSignedThousandthsFloat(buffer, AHRS_UPDATE_LINEAR_ACCEL_Z_VALUE_INDEX)
        self.cal_mag_x = IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_CAL_MAG_X_VALUE_INDEX)
        self.cal_mag_y = IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_CAL_MAG_Y_VALUE_INDEX)
        self.cal_mag_z = IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_CAL_MAG_Z_VALUE_INDEX)
        self.mag_field_norm_ratio = IMURegisters.decodeProtocolUnsignedHundredthsFloat(buffer, AHRS_UPDATE_CAL_MAG_NORM_RATIO_VALUE_INDEX)
        self.mag_field_norm_scalar = IMURegisters.decodeProtocol1616Float(buffer, AHRS_UPDATE_CAL_MAG_SCALAR_VALUE_INDEX)
        self.mpu_temp = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRS_UPDATE_MPU_TEMP_VAUE_INDEX)
        self.raw_mag_x = IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_RAW_MAG_X_VALUE_INDEX)
        self.raw_mag_y = IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_RAW_MAG_Y_VALUE_INDEX)
        self.raw_mag_z = IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_RAW_MAG_Z_VALUE_INDEX)
        # AHRSPosUpdate:  Quaternions are signed int (16-bit resolution); divide by 16384 to yield +/- 2 radians
        self.quat_w = float(IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_QUAT_W_VALUE_INDEX)) / 16384.0
        self.quat_x = float(IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_QUAT_X_VALUE_INDEX)) / 16384.0
        self.quat_y = float(IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_QUAT_Y_VALUE_INDEX)) / 16384.0
        self.quat_z = float(IMURegisters.decodeProtocolInt16(buffer, AHRS_UPDATE_QUAT_Z_VALUE_INDEX)) / 16384.0
        self.barometric_pressure = IMURegisters.decodeProtocol1616Float(buffer, AHRS_UPDATE_BARO_PRESSURE_VALUE_INDEX)
        self.baro_temp = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRS_UPDATE_BARO_TEMP_VAUE_INDEX)
        self.op_status = buffer[AHRS_UPDATE_OPSTATUS_VALUE_INDEX]
        self.sensor_status = buffer[AHRS_UPDATE_SENSOR_STATUS_VALUE_INDEX]
        self.cal_status = buffer[AHRS_UPDATE_CAL_STATUS_VALUE_INDEX]
        self.selftest_status = buffer[AHRS_UPDATE_SELFTEST_STATUS_VALUE_INDEX]

        return AHRS_UPDATE_MESSAGE_LENGTH

class AHRSPosUpdate(AHRSUpdateBase):
    vel_x: float
    vel_y: float
    vel_z: float
    disp_x: float
    disp_y: float
    disp_z: float

    def encode(self, protocol_buffer: bytearray):
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
        protocol_buffer[2] = AHRSPOS_UPDATE_MESSAGE_LENGTH - 2
        protocol_buffer[3] = MSGID_AHRSPOS_UPDATE
        # data
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.yaw, protocol_buffer, AHRSPOS_UPDATE_YAW_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.pitch, protocol_buffer, AHRSPOS_UPDATE_PITCH_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.roll, protocol_buffer, AHRSPOS_UPDATE_ROLL_VALUE_INDEX)
        IMURegisters.encodeProtocolUnsignedHundredthsFloat(self.compass_heading, protocol_buffer, AHRSPOS_UPDATE_HEADING_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.altitude,protocol_buffer, AHRSPOS_UPDATE_ALTITUDE_VALUE_INDEX)
        IMURegisters.encodeProtocolUnsignedHundredthsFloat(self.fused_heading, protocol_buffer, AHRSPOS_UPDATE_FUSED_HEADING_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedThousandthsFloat(self.linear_accel_x,protocol_buffer, AHRSPOS_UPDATE_LINEAR_ACCEL_X_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedThousandthsFloat(self.linear_accel_y,protocol_buffer, AHRSPOS_UPDATE_LINEAR_ACCEL_Y_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedThousandthsFloat(self.linear_accel_z,protocol_buffer, AHRSPOS_UPDATE_LINEAR_ACCEL_Z_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.vel_x,protocol_buffer, AHRSPOS_UPDATE_VEL_X_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.vel_y,protocol_buffer, AHRSPOS_UPDATE_VEL_Y_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.vel_z,protocol_buffer, AHRSPOS_UPDATE_VEL_Z_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.disp_x,protocol_buffer, AHRSPOS_UPDATE_DISP_X_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.disp_y,protocol_buffer, AHRSPOS_UPDATE_DISP_Y_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.disp_z,protocol_buffer, AHRSPOS_UPDATE_DISP_Z_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.mpu_temp_c, protocol_buffer, AHRSPOS_UPDATE_MPU_TEMP_VAUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.quat_w, protocol_buffer, AHRSPOS_UPDATE_QUAT_W_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.quat_x, protocol_buffer, AHRSPOS_UPDATE_QUAT_X_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.quat_y, protocol_buffer, AHRSPOS_UPDATE_QUAT_Y_VALUE_INDEX)
        IMURegisters.encodeProtocolInt16(self.quat_z, protocol_buffer, AHRSPOS_UPDATE_QUAT_Z_VALUE_INDEX)

        protocol_buffer[AHRSPOS_UPDATE_OPSTATUS_VALUE_INDEX] = self.op_status
        protocol_buffer[AHRSPOS_UPDATE_SENSOR_STATUS_VALUE_INDEX] = self.sensor_status
        protocol_buffer[AHRSPOS_UPDATE_CAL_STATUS_VALUE_INDEX] = self.cal_status
        protocol_buffer[AHRSPOS_UPDATE_SELFTEST_STATUS_VALUE_INDEX] = self.selftest_status
        # Footer
        encodeTermination( protocol_buffer, AHRSPOS_UPDATE_MESSAGE_LENGTH, AHRSPOS_UPDATE_MESSAGE_LENGTH - 4 )
        return AHRSPOS_UPDATE_MESSAGE_LENGTH

    def decode(self, buffer: bytes) -> Optional[int]:
        if not verifyPrefixBin(buffer, AHRSPOS_UPDATE_MESSAGE_LENGTH, MSGID_AHRS_UPDATE, AHRSPOS_UPDATE_MESSAGE_CHECKSUM_INDEX):
            return None
        self.yaw = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRSPOS_UPDATE_YAW_VALUE_INDEX)
        self.pitch = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRSPOS_UPDATE_PITCH_VALUE_INDEX)
        self.roll = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRSPOS_UPDATE_ROLL_VALUE_INDEX)
        self.compass_heading = IMURegisters.decodeProtocolUnsignedHundredthsFloat(buffer, AHRSPOS_UPDATE_HEADING_VALUE_INDEX)
        self.altitude = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_UPDATE_ALTITUDE_VALUE_INDEX)
        self.fused_heading = IMURegisters.decodeProtocolUnsignedHundredthsFloat(buffer, AHRSPOS_UPDATE_FUSED_HEADING_VALUE_INDEX)
        self.linear_accel_x = IMURegisters.decodeProtocolSignedThousandthsFloat(buffer, AHRSPOS_UPDATE_LINEAR_ACCEL_X_VALUE_INDEX)
        self.linear_accel_y = IMURegisters.decodeProtocolSignedThousandthsFloat(buffer, AHRSPOS_UPDATE_LINEAR_ACCEL_Y_VALUE_INDEX)
        self.linear_accel_z = IMURegisters.decodeProtocolSignedThousandthsFloat(buffer, AHRSPOS_UPDATE_LINEAR_ACCEL_Z_VALUE_INDEX)
        self.vel_x = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_UPDATE_VEL_X_VALUE_INDEX)
        self.vel_y = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_UPDATE_VEL_Y_VALUE_INDEX)
        self.vel_z = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_UPDATE_VEL_Z_VALUE_INDEX)
        self.disp_x = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_UPDATE_DISP_X_VALUE_INDEX)
        self.disp_y = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_UPDATE_DISP_Y_VALUE_INDEX)
        self.disp_z = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_UPDATE_DISP_Z_VALUE_INDEX)
        self.mpu_temp = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRSPOS_UPDATE_MPU_TEMP_VAUE_INDEX)
        # AHRSPosUpdate:  Quaternions are signed int (16-bit resolution); divide by 16384 to yield +/- 2 radians
        self.quat_w = float(IMURegisters.decodeProtocolInt16(buffer, AHRSPOS_UPDATE_QUAT_W_VALUE_INDEX)) / 16384.0
        self.quat_x = float(IMURegisters.decodeProtocolInt16(buffer, AHRSPOS_UPDATE_QUAT_X_VALUE_INDEX)) / 16384.0
        self.quat_y = float(IMURegisters.decodeProtocolInt16(buffer, AHRSPOS_UPDATE_QUAT_Y_VALUE_INDEX)) / 16384.0
        self.quat_z = float(IMURegisters.decodeProtocolInt16(buffer, AHRSPOS_UPDATE_QUAT_Z_VALUE_INDEX)) / 16384.0
        self.op_status = buffer[AHRSPOS_UPDATE_OPSTATUS_VALUE_INDEX]
        self.sensor_status = buffer[AHRSPOS_UPDATE_SENSOR_STATUS_VALUE_INDEX]
        self.cal_status = buffer[AHRSPOS_UPDATE_CAL_STATUS_VALUE_INDEX]
        self.selftest_status = buffer[AHRSPOS_UPDATE_SELFTEST_STATUS_VALUE_INDEX]

        return AHRSPOS_UPDATE_MESSAGE_LENGTH

class AHRSPosTSUpdate(AHRSPosUpdate):
    timestamp: int

    def encode(self, protocol_buffer: bytearray) -> int:
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
        protocol_buffer[2] = AHRSPOS_TS_UPDATE_MESSAGE_LENGTH - 2
        protocol_buffer[3] = MSGID_AHRSPOS_TS_UPDATE

        # data
        IMURegisters.encodeProtocol1616Float(self.yaw, protocol_buffer, AHRSPOS_TS_UPDATE_YAW_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.pitch, protocol_buffer, AHRSPOS_TS_UPDATE_PITCH_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.roll, protocol_buffer, AHRSPOS_TS_UPDATE_ROLL_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.compass_heading, protocol_buffer, AHRSPOS_TS_UPDATE_HEADING_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.altitude,protocol_buffer, AHRSPOS_TS_UPDATE_ALTITUDE_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.fused_heading, protocol_buffer, AHRSPOS_TS_UPDATE_FUSED_HEADING_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.linear_accel_x,protocol_buffer, AHRSPOS_TS_UPDATE_LINEAR_ACCEL_X_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.linear_accel_y,protocol_buffer, AHRSPOS_TS_UPDATE_LINEAR_ACCEL_Y_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.linear_accel_z,protocol_buffer, AHRSPOS_TS_UPDATE_LINEAR_ACCEL_Z_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.vel_x,protocol_buffer, AHRSPOS_TS_UPDATE_VEL_X_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.vel_y,protocol_buffer, AHRSPOS_TS_UPDATE_VEL_Y_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.vel_z,protocol_buffer, AHRSPOS_TS_UPDATE_VEL_Z_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.disp_x,protocol_buffer, AHRSPOS_TS_UPDATE_DISP_X_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.disp_y,protocol_buffer, AHRSPOS_TS_UPDATE_DISP_Y_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.disp_z,protocol_buffer, AHRSPOS_TS_UPDATE_DISP_Z_VALUE_INDEX)
        IMURegisters.encodeProtocolSignedHundredthsFloat(self.mpu_temp_c, protocol_buffer, AHRSPOS_TS_UPDATE_MPU_TEMP_VAUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.quat_w, protocol_buffer, AHRSPOS_TS_UPDATE_QUAT_W_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.quat_x, protocol_buffer, AHRSPOS_TS_UPDATE_QUAT_X_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.quat_y, protocol_buffer, AHRSPOS_TS_UPDATE_QUAT_Y_VALUE_INDEX)
        IMURegisters.encodeProtocol1616Float(self.quat_z, protocol_buffer, AHRSPOS_TS_UPDATE_QUAT_Z_VALUE_INDEX)

        protocol_buffer[AHRSPOS_TS_UPDATE_OPSTATUS_VALUE_INDEX] = self.op_status
        protocol_buffer[AHRSPOS_TS_UPDATE_SENSOR_STATUS_VALUE_INDEX] = self.sensor_status
        protocol_buffer[AHRSPOS_TS_UPDATE_CAL_STATUS_VALUE_INDEX] = self.cal_status
        protocol_buffer[AHRSPOS_TS_UPDATE_SELFTEST_STATUS_VALUE_INDEX] = self.selftest_status
        IMURegisters.encodeProtocolInt32(self.timestamp, protocol_buffer, AHRSPOS_TS_UPDATE_TIMESTAMP_INDEX)

        # Footer
        encodeTermination( protocol_buffer, AHRSPOS_TS_UPDATE_MESSAGE_LENGTH, AHRSPOS_TS_UPDATE_MESSAGE_LENGTH - 4 )
        return AHRSPOS_TS_UPDATE_MESSAGE_LENGTH

    def decode(self, buffer: bytes) -> Optional[int]:
        if not verifyPrefix(buffer, AHRSPOS_TS_UPDATE_MESSAGE_LENGTH, [PACKET_START_CHAR, BINARY_PACKET_INDICATOR_CHAR, AHRSPOS_TS_UPDATE_MESSAGE_LENGTH - 2, MSGID_AHRSPOS_TS_UPDATE], AHRSPOS_TS_UPDATE_MESSAGE_CHECKSUM_INDEX):
            return None

        self.yaw = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_YAW_VALUE_INDEX)
        self.pitch = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_PITCH_VALUE_INDEX)
        self.roll = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_ROLL_VALUE_INDEX)
        self.compass_heading = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_HEADING_VALUE_INDEX)
        self.altitude = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_ALTITUDE_VALUE_INDEX)
        self.fused_heading = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_FUSED_HEADING_VALUE_INDEX)
        self.linear_accel_x = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_LINEAR_ACCEL_X_VALUE_INDEX)
        self.linear_accel_y = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_LINEAR_ACCEL_Y_VALUE_INDEX)
        self.linear_accel_z = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_LINEAR_ACCEL_Z_VALUE_INDEX)
        self.vel_x = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_VEL_X_VALUE_INDEX)
        self.vel_y = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_VEL_Y_VALUE_INDEX)
        self.vel_z = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_VEL_Z_VALUE_INDEX)
        self.disp_x = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_DISP_X_VALUE_INDEX)
        self.disp_y = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_DISP_Y_VALUE_INDEX)
        self.disp_z = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_DISP_Z_VALUE_INDEX)
        self.mpu_temp = IMURegisters.decodeProtocolSignedHundredthsFloat(buffer, AHRSPOS_TS_UPDATE_MPU_TEMP_VAUE_INDEX)
        self.quat_w = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_QUAT_W_VALUE_INDEX) / 16384.0
        self.quat_x = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_QUAT_X_VALUE_INDEX) / 16384.0
        self.quat_y = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_QUAT_Y_VALUE_INDEX) / 16384.0
        self.quat_z = IMURegisters.decodeProtocol1616Float(buffer, AHRSPOS_TS_UPDATE_QUAT_Z_VALUE_INDEX) / 16384.0
        self.op_status = buffer[AHRSPOS_TS_UPDATE_OPSTATUS_VALUE_INDEX]
        self.sensor_status = buffer[AHRSPOS_TS_UPDATE_SENSOR_STATUS_VALUE_INDEX]
        self.cal_status = buffer[AHRSPOS_TS_UPDATE_CAL_STATUS_VALUE_INDEX]
        self.selftest_status = buffer[AHRSPOS_TS_UPDATE_SELFTEST_STATUS_VALUE_INDEX]
        self.timestamp = np.uint32(IMURegisters.decodeProtocolInt32(buffer, AHRSPOS_TS_UPDATE_TIMESTAMP_INDEX))

        return AHRSPOS_UPDATE_MESSAGE_LENGTH

@dataclass
class BoardID:
    type: int
    hw_rev: int
    fw_ver_major: int
    fw_ver_minor: int
    fw_revision: int
    unique_id: list[int]

    def encode(self, protocol_buffer: bytearray) -> int:
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
        protocol_buffer[2] = BOARD_IDENTITY_RESPONSE_MESSAGE_LENGTH - 2
        protocol_buffer[3] = MSGID_BOARD_IDENTITY_RESPONSE
        # Data
        protocol_buffer[BOARD_IDENTITY_BOARDTYPE_VALUE_INDEX] = self.type
        protocol_buffer[BOARD_IDENTITY_HWREV_VALUE_INDEX] = self.hw_rev
        protocol_buffer[BOARD_IDENTITY_FW_VER_MAJOR] = self.fw_ver_major
        protocol_buffer[BOARD_IDENTITY_FW_VER_MINOR] = self.fw_ver_minor
        IMURegisters.encodeProtocolUint16(self.fw_revision, protocol_buffer, BOARD_IDENTITY_FW_VER_REVISION_VALUE_INDEX)
        for i in range(12):
            protocol_buffer[BOARD_IDENTITY_UNIQUE_ID_0 + i] = self.unique_id[i]
        # Footer
        encodeTermination( protocol_buffer, BOARD_IDENTITY_RESPONSE_MESSAGE_LENGTH, BOARD_IDENTITY_RESPONSE_MESSAGE_LENGTH - 4 )
        return BOARD_IDENTITY_RESPONSE_MESSAGE_LENGTH
    
    def decode(self, buffer: bytes) -> Optional[int]:
        if not verifyPrefix(buffer, BOARD_IDENTITY_RESPONSE_MESSAGE_LENGTH, [PACKET_START_CHAR, BINARY_PACKET_INDICATOR_CHAR, BOARD_IDENTITY_RESPONSE_MESSAGE_LENGTH - 2, MSGID_BOARD_IDENTITY_RESPONSE], BOARD_IDENTITY_RESPONSE_CHECKSUM_INDEX):
            return None

        self.type = buffer[BOARD_IDENTITY_BOARDTYPE_VALUE_INDEX]
        self.hw_rev = buffer[BOARD_IDENTITY_HWREV_VALUE_INDEX]
        self.fw_ver_major = buffer[BOARD_IDENTITY_FW_VER_MAJOR]
        self.fw_ver_minor = buffer[BOARD_IDENTITY_FW_VER_MINOR]
        self.fw_revision = IMURegisters.decodeProtocolUint16(buffer, BOARD_IDENTITY_FW_VER_REVISION_VALUE_INDEX)
        self.unique_id = np.array(12, dtype=np.uint8)
        for i in range(12):
            self.unique_id[i] = buffer[BOARD_IDENTITY_UNIQUE_ID_0 + i]
        return BOARD_IDENTITY_RESPONSE_MESSAGE_LENGTH


# Integration Control Command Packet
MSGID_INTEGRATION_CONTROL_CMD = 'I'
INTEGRATION_CONTROL_CMD_ACTION_INDEX =                4
INTEGRATION_CONTROL_CMD_PARAMETER_INDEX =             5
INTEGRATION_CONTROL_CMD_MESSAGE_CHECKSUM_INDEX =      9
INTEGRATION_CONTROL_CMD_MESSAGE_TERMINATOR_INDEX =    11
INTEGRATION_CONTROL_CMD_MESSAGE_LENGTH =              13

# Integration Control Response Packet
MSGID_INTEGRATION_CONTROL_RESP = 'j'
INTEGRATION_CONTROL_RESP_ACTION_INDEX =               4
INTEGRATION_CONTROL_RESP_PARAMETER_INDEX =            5
INTEGRATION_CONTROL_RESP_MESSAGE_CHECKSUM_INDEX =     9
INTEGRATION_CONTROL_RESP_MESSAGE_TERMINATOR_INDEX =   11
INTEGRATION_CONTROL_RESP_MESSAGE_LENGTH =             13

@dataclass
class IntegrationControl:
    action: np.uint8 = np.uint8(0)
    parameter: int = 0

    def encode(self, protocol_buffer: bytearray) -> int:
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
        protocol_buffer[2] = INTEGRATION_CONTROL_CMD_MESSAGE_LENGTH - 2
        protocol_buffer[3] = MSGID_INTEGRATION_CONTROL_CMD
        # Data
        protocol_buffer[INTEGRATION_CONTROL_CMD_ACTION_INDEX] = self.action
        IMURegisters.encodeProtocolInt32(self.parameter, protocol_buffer, INTEGRATION_CONTROL_CMD_PARAMETER_INDEX)
        # Footer
        encodeTermination( protocol_buffer, INTEGRATION_CONTROL_CMD_MESSAGE_LENGTH, INTEGRATION_CONTROL_CMD_MESSAGE_LENGTH - 4 )
        return INTEGRATION_CONTROL_CMD_MESSAGE_LENGTH
    
    def decode(self, buffer: bytes) -> Optional[int]:
        pfx = [PACKET_START_CHAR, BINARY_PACKET_INDICATOR_CHAR, INTEGRATION_CONTROL_CMD_MESSAGE_LENGTH - 2, MSGID_INTEGRATION_CONTROL_CMD]
        if not verifyPrefix(buffer, INTEGRATION_CONTROL_CMD_MESSAGE_LENGTH, pfx, INTEGRATION_CONTROL_CMD_MESSAGE_CHECKSUM_INDEX):
            return None

        # Data
        self.action = np.uint8(buffer[INTEGRATION_CONTROL_CMD_ACTION_INDEX])
        self.parameter = decodeProtocolInt32(buffer, INTEGRATION_CONTROL_CMD_PARAMETER_INDEX)
        return INTEGRATION_CONTROL_CMD_MESSAGE_LENGTH

    def encode_response(self, protocol_buffer: bytearray):
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
        protocol_buffer[2] = INTEGRATION_CONTROL_RESP_MESSAGE_LENGTH - 2
        protocol_buffer[3] = MSGID_INTEGRATION_CONTROL_RESP
        # Data
        protocol_buffer[INTEGRATION_CONTROL_RESP_ACTION_INDEX] = self.action
        IMURegisters.encodeProtocolInt32(self.parameter, protocol_buffer, INTEGRATION_CONTROL_RESP_PARAMETER_INDEX)
        # Footer
        encodeTermination( protocol_buffer, INTEGRATION_CONTROL_RESP_MESSAGE_LENGTH, INTEGRATION_CONTROL_RESP_MESSAGE_LENGTH - 4 )
        return INTEGRATION_CONTROL_RESP_MESSAGE_LENGTH

    def decode_response(self, buffer: bytes) -> Optional[int]:
        pfx = [PACKET_START_CHAR, BINARY_PACKET_INDICATOR_CHAR, INTEGRATION_CONTROL_RESP_MESSAGE_LENGTH - 2, MSGID_INTEGRATION_CONTROL_RESP]
        if not verifyPrefix(buffer, INTEGRATION_CONTROL_RESP_MESSAGE_LENGTH, pfx, INTEGRATION_CONTROL_RESP_MESSAGE_CHECKSUM_INDEX):
            return None
        # Data
        self.action = np.uint8(buffer[INTEGRATION_CONTROL_RESP_ACTION_INDEX])
        self.parameter = IMURegisters.decodeProtocolInt32(buffer, INTEGRATION_CONTROL_RESP_PARAMETER_INDEX)
        return INTEGRATION_CONTROL_RESP_MESSAGE_LENGTH

"""
def encodeTuningVariableCmd( char *protocol_buffer, AHRS_DATA_ACTION getset, AHRS_TUNING_VAR_ID id, float val ):
    # Header
    protocol_buffer[0] = PACKET_START_CHAR
    protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
    protocol_buffer[2] = FUSION_TUNING_CMD_MESSAGE_LENGTH - 2
    protocol_buffer[3] = MSGID_FUSION_TUNING_CMD
    # Data
    protocol_buffer[FUSION_TUNING_DATA_ACTION_VALUE_INDEX] = getset
    protocol_buffer[FUSION_TUNING_CMD_VAR_ID_VALUE_INDEX] = id
    IMURegisters.encodeProtocol1616Float(val,protocol_buffer, FUSION_TUNING_CMD_VAR_VALUE_INDEX)
    # Footer
    encodeTermination( protocol_buffer, FUSION_TUNING_CMD_MESSAGE_LENGTH, FUSION_TUNING_CMD_MESSAGE_LENGTH - 4 )
    return FUSION_TUNING_CMD_MESSAGE_LENGTH

def decodeTuningVariableCmd(buffer: bytes, AHRS_DATA_ACTION& getset, AHRS_TUNING_VAR_ID& id, float& val ):
    if not verifyPrefix(buffer, FUSION_TUNING_CMD_MESSAGE_LENGTH, )
    if ( length < FUSION_TUNING_CMD_MESSAGE_LENGTH ) return 0
    if ( ( buffer[0] == PACKET_START_CHAR ) and
            ( buffer[1] == BINARY_PACKET_INDICATOR_CHAR ) and
            ( buffer[2] == FUSION_TUNING_CMD_MESSAGE_LENGTH - 2) and
            ( buffer[3] == MSGID_FUSION_TUNING_CMD ) )
    {
        if ( !verifyChecksum( buffer, FUSION_TUNING_CMD_MESSAGE_CHECKSUM_INDEX ) ) return 0

        # Data
        getset = (AHRS_DATA_ACTION)buffer[FUSION_TUNING_DATA_ACTION_VALUE_INDEX]
        id = (AHRS_TUNING_VAR_ID)buffer[FUSION_TUNING_CMD_VAR_ID_VALUE_INDEX]
        val = IMURegisters.decodeProtocol1616Float(buffer, FUSION_TUNING_CMD_VAR_VALUE_INDEX)
        return FUSION_TUNING_CMD_MESSAGE_LENGTH
    }
    return 0


def encodeMagCalCommand(protocol_buffer: bytearray, action: AHRS_DATA_ACTION, int16_t *bias, float *matrix, float earth_mag_field_norm ) -> int:
    # Header
    protocol_buffer[0] = PACKET_START_CHAR
    protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
    protocol_buffer[2] = MAG_CAL_CMD_MESSAGE_LENGTH - 2
    protocol_buffer[3] = MSGID_MAG_CAL_CMD

    # Data
    protocol_buffer[MAG_CAL_DATA_ACTION_VALUE_INDEX] = action
    for ( int i = 0; i < 3; i++ ) {
        IMURegisters.encodeProtocolInt16(	bias[i],
                &protocol_buffer[MAG_X_BIAS_VALUE_INDEX + (i * sizeof(int16_t))])
    }
    for ( int i = 0; i < 9; i++ ) {
        IMURegisters.encodeProtocol1616Float( matrix[i], &protocol_buffer[MAG_XFORM_1_1_VALUE_INDEX + (i * sizeof(s_1616_float))])
    }
    IMURegisters.encodeProtocol1616Float( earth_mag_field_norm, protocol_buffer, MAG_CAL_EARTH_MAG_FIELD_NORM_VALUE_INDEX)
    # Footer
    encodeTermination( protocol_buffer, MAG_CAL_CMD_MESSAGE_LENGTH, MAG_CAL_CMD_MESSAGE_LENGTH - 4 )
    return MAG_CAL_CMD_MESSAGE_LENGTH
}

def decodeMagCalCommand( char *buffer, int length,
        AHRS_DATA_ACTION& action,
        int16_t *bias,
        float *matrix,
        float& earth_mag_field_norm)
{
    if ( length < MAG_CAL_CMD_MESSAGE_LENGTH ) return 0
    if ( ( buffer[0] == PACKET_START_CHAR ) and
            ( buffer[1] == BINARY_PACKET_INDICATOR_CHAR ) and
            ( buffer[2] == MAG_CAL_CMD_MESSAGE_LENGTH - 2) and
            ( buffer[3] == MSGID_MAG_CAL_CMD ) ) {

        if ( !verifyChecksum( buffer, MAG_CAL_CMD_MESSAGE_CHECKSUM_INDEX ) ) return 0

        action = (AHRS_DATA_ACTION)buffer[MAG_CAL_DATA_ACTION_VALUE_INDEX]
        for ( int i = 0; i < 3; i++ ) {
            bias[i] = IMURegisters.decodeProtocolInt16(&buffer[MAG_X_BIAS_VALUE_INDEX + (i * sizeof(int16_t))])
        }
        for ( int i = 0; i < 9; i++ ) {
            matrix[i] = IMURegisters.decodeProtocol1616Float(&buffer[MAG_XFORM_1_1_VALUE_INDEX + (i * sizeof(s_1616_float))])
        }
        earth_mag_field_norm = IMURegisters.decodeProtocol1616Float(buffer, MAG_CAL_EARTH_MAG_FIELD_NORM_VALUE_INDEX)
        return MAG_CAL_CMD_MESSAGE_LENGTH
    }
    return 0
}

static int encodeDataSetResponse( char *protocol_buffer, AHRS_DATA_TYPE type, AHRS_TUNING_VAR_ID subtype, uint8_t status )
{
    # Header
    protocol_buffer[0] = PACKET_START_CHAR
    protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
    protocol_buffer[2] = DATA_SET_RESPONSE_MESSAGE_LENGTH - 2
    protocol_buffer[3] = MSGID_DATA_SET_RESPONSE
    # Data
    protocol_buffer[DATA_SET_RESPONSE_DATATYPE_VALUE_INDEX] = type
    protocol_buffer[DATA_SET_RESPONSE_VARID_VALUE_INDEX] = subtype
    protocol_buffer[DATA_SET_RESPONSE_STATUS_VALUE_INDEX] = status
    # Footer
    encodeTermination( protocol_buffer, DATA_SET_RESPONSE_MESSAGE_LENGTH, DATA_SET_RESPONSE_MESSAGE_LENGTH - 4 )
    return DATA_SET_RESPONSE_MESSAGE_LENGTH
}

static int decodeDataSetResponse( char *buffer, int length, AHRS_DATA_TYPE &type, AHRS_TUNING_VAR_ID &subtype, uint8_t& status )
{
    if ( length < DATA_SET_RESPONSE_MESSAGE_LENGTH ) return 0
    if ( ( buffer[0] == PACKET_START_CHAR ) and
            ( buffer[1] == BINARY_PACKET_INDICATOR_CHAR ) and
            ( buffer[2] == DATA_SET_RESPONSE_MESSAGE_LENGTH - 2) and
            ( buffer[3] == MSGID_DATA_SET_RESPONSE ) ) {

        if ( !verifyChecksum( buffer, DATA_SET_RESPONSE_MESSAGE_CHECKSUM_INDEX ) ) return 0

        type = (AHRS_DATA_TYPE)buffer[DATA_SET_RESPONSE_DATATYPE_VALUE_INDEX]
        subtype = (AHRS_TUNING_VAR_ID)buffer[DATA_SET_RESPONSE_VARID_VALUE_INDEX]
        status = buffer[DATA_SET_RESPONSE_STATUS_VALUE_INDEX]
        return DATA_SET_RESPONSE_MESSAGE_LENGTH
    }
    return 0
}

static int encodeDataGetRequest( char *protocol_buffer, AHRS_DATA_TYPE type, AHRS_TUNING_VAR_ID subtype )
{
    # Header
    protocol_buffer[0] = PACKET_START_CHAR
    protocol_buffer[1] = BINARY_PACKET_INDICATOR_CHAR
    protocol_buffer[2] = DATA_REQUEST_MESSAGE_LENGTH - 2
    protocol_buffer[3] = MSGID_DATA_REQUEST
    # Data
    protocol_buffer[DATA_REQUEST_DATATYPE_VALUE_INDEX] = type
    protocol_buffer[DATA_REQUEST_VARIABLEID_VALUE_INDEX] = subtype
    # Footer
    encodeTermination( protocol_buffer, DATA_REQUEST_MESSAGE_LENGTH, DATA_REQUEST_MESSAGE_LENGTH - 4 )
    return DATA_REQUEST_MESSAGE_LENGTH
}

static int decodeDataGetRequest( char *buffer, int length, AHRS_DATA_TYPE& type, AHRS_TUNING_VAR_ID& subtype )
{
    if ( length < DATA_REQUEST_MESSAGE_LENGTH ) return 0
    if ( ( buffer[0] == PACKET_START_CHAR ) and
            ( buffer[1] == BINARY_PACKET_INDICATOR_CHAR ) and
            ( buffer[2] == DATA_REQUEST_MESSAGE_LENGTH - 2) and
            ( buffer[3] == MSGID_DATA_REQUEST ) ) {

        if ( !verifyChecksum( buffer, DATA_REQUEST_CHECKSUM_INDEX ) ) return 0

        type = (AHRS_DATA_TYPE)buffer[DATA_REQUEST_DATATYPE_VALUE_INDEX]
        subtype = (AHRS_TUNING_VAR_ID)buffer[DATA_REQUEST_VARIABLEID_VALUE_INDEX]

        return DATA_REQUEST_MESSAGE_LENGTH
    }
    return 0
}"""