from typing import Union, Optional, Iterable
from dataclasses import dataclass
from io import TextIOBase
import numpy as np

PACKET_START_CHAR = '!'
CHECKSUM_LENGTH = 2 #  8-bit checksump, all bytes before checksum 
TERMINATOR_LENGTH = 2 #  Carriage Return, Line Feed 

PROTOCOL_FLOAT_LENGTH = 7


def encodeTermination(buffer: bytearray, total_length: int, content_length: int ):
    if ( ( total_length >= (CHECKSUM_LENGTH + TERMINATOR_LENGTH) ) and ( total_length >= content_length + (CHECKSUM_LENGTH + TERMINATOR_LENGTH) ) ):
        # Checksum
        checksum = 0
        for c in buffer[:content_length]:
            checksum += c
        # convert checksum to two ascii bytes
        buffer[content_length:content_length+2] = bytes(f"{checksum:#02X}", 'ascii')
        # Message Terminator
        buffer[content_length + CHECKSUM_LENGTH: content_length + CHECKSUM_LENGTH + 2] = b"\r\n"

NAV6_FLAG_MASK_CALIBRATION_STATE = 0x03
NAV6_CALIBRATION_STATE_WAIT = 0x00
NAV6_CALIBRATION_STATE_ACCUMULATE = 0x01
NAV6_CALIBRATION_STATE_COMPLETE = 0x02

def decode_hex(src: str) -> int:
    if isinstance(src, str):
        src = ord(src)
    return src - ord('0') if src <= ord('9') else ((src - ord('A')) + 10)

def decodeUint8(buffer: bytes, offset: int = 0) -> np.uint8:
    checksum = buffer[offset:offset+2]
    first_digit =  decode_hex(checksum[0])
    second_digit = decode_hex(checksum[1])
    decoded_checksum = np.uint8((first_digit * 16) + second_digit)
    return decoded_checksum

def decodeProtocolFloat(src: Union[TextIOBase, bytes], offset: int = 0) -> float:
    if isinstance(src, bytes):
        temp = src[offset:offset+PROTOCOL_FLOAT_LENGTH]
    else:
        temp = src.read(PROTOCOL_FLOAT_LENGTH)
    assert len(temp) == PROTOCOL_FLOAT_LENGTH
    return float(temp)


def encodeProtocolFloat(f: float, buffer: bytearray, offset: int = 0):
    """
    Formats a float as follows
    e.g., -129.235
    "-129.24"
    e.g., 23.4
    "+023.40
    """
    work_buffer = f"{f:+07.02f}"[-7:]
    if work_buffer[0] == '+':
        work_buffer = ' ' + work_buffer[1:]
    buffer[offset:offset+PROTOCOL_FLOAT_LENGTH] = bytes(work_buffer, 'ascii')

def encodeProtocolUint16(value: np.uint16, dst: bytearray, offset: int = 0):
    value = np.uint16(value)
    dst[offset:offset+4] = bytes(f"{value:#04X}", 'ascii')

def decodeProtocolUint16(buffer: bytes, offset: int = 0) -> np.uint16:
    decoded_uint16 = 0
    shift_left = 12
    for i in range(4):
        digit = np.uint16(decode_hex(buffer[i]))
        decoded_uint16 += (digit << shift_left)
        shift_left -= 4
    return decoded_uint16

# 0 to 655.35
def decodeProtocolUnsignedHundredthsFloat(buffer: bytes, offset: int = 0) -> float:
    unsigned_float = float(decodeProtocolUint16(buffer, offset))
    return unsigned_float / 100.0
def encodeProtocolUnsignedHundredthsFloat(value: float, buffer: bytes, offset: int = 0):
    input_as_uint = np.uint16(value * 100.0)
    return encodeProtocolUint16(input_as_uint, buffer, offset)

def verifyChecksum(buffer: bytes, content_length: int) -> bool:
    # Calculate Checksum
    checksum = np.uint8(0)
    for c in buffer[0:content_length]:
        checksum += c

    # Decode Checksum
    decoded_checksum = decodeUint8(buffer[content_length] )

    return np.uint8(checksum) == decoded_checksum

def verifyPrefix(buffer: bytes, length: int, prefix: Iterable[int], checksum_idx: Optional[int] = None) -> bool:
    if len(buffer) < length:
        return False
    for i in range(len(prefix)):
        if buffer[i] != int(prefix[i]):
            return False
    if checksum_idx is not None:
        if not verifyChecksum(buffer, checksum_idx):
            return False
    return True



# Yaw/Pitch/Roll (YPR) Update Packet - e.g., !y[yaw][pitch][roll][compass]
# (All values as floats)

MSGID_YPR_UPDATE = 'y'
YPR_UPDATE_YAW_VALUE_INDEX = 2
YPR_UPDATE_ROLL_VALUE_INDEX = 9
YPR_UPDATE_PITCH_VALUE_INDEX = 16
YPR_UPDATE_COMPASS_VALUE_INDEX = 23
YPR_UPDATE_CHECKSUM_INDEX = 30
YPR_UPDATE_TERMINATOR_INDEX = 32
YPR_UPDATE_MESSAGE_LENGTH = 34

@dataclass
class YPRUpdate:
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    compass_heading: float = 0.0
    
    def encode(self, protocol_buffer: bytearray) -> int:
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = MSGID_YPR_UPDATE

        # Data
        encodeProtocolFloat(self.yaw,    protocol_buffer, YPR_UPDATE_YAW_VALUE_INDEX )
        encodeProtocolFloat(self.pitch,  protocol_buffer, YPR_UPDATE_PITCH_VALUE_INDEX )
        encodeProtocolFloat(self.roll,   protocol_buffer, YPR_UPDATE_ROLL_VALUE_INDEX )
        encodeProtocolFloat(self.compass_heading, protocol_buffer, YPR_UPDATE_COMPASS_VALUE_INDEX )

        # Footer
        encodeTermination( protocol_buffer, YPR_UPDATE_MESSAGE_LENGTH, YPR_UPDATE_MESSAGE_LENGTH - 4 )

        return YPR_UPDATE_MESSAGE_LENGTH
    def decode(self, buffer: bytes) -> Optional[int]:
        if not verifyPrefix(buffer, YPR_UPDATE_MESSAGE_LENGTH, ['!', 'y'], checksum_idx=YPR_UPDATE_CHECKSUM_INDEX):
            return None
        self.yaw             = decodeProtocolFloat(buffer, YPR_UPDATE_YAW_VALUE_INDEX)
        self.pitch           = decodeProtocolFloat(buffer, YPR_UPDATE_PITCH_VALUE_INDEX)
        self.roll            = decodeProtocolFloat(buffer, YPR_UPDATE_ROLL_VALUE_INDEX)
        self.compass_heading = decodeProtocolFloat(buffer, YPR_UPDATE_COMPASS_VALUE_INDEX)
        return YPR_UPDATE_MESSAGE_LENGTH



# Gyro/Raw Data Update packet - e.g., !g[gx][gy][gz][accelx][accely][accelz][magx][magy][magz][temp_c]

MSGID_GYRO_UPDATE = 'g'
GYRO_UPDATE_MESSAGE_LENGTH = 46
GYRO_UPDATE_GYRO_X_VALUE_INDEX = 2
GYRO_UPDATE_GYRO_Y_VALUE_INDEX = 6
GYRO_UPDATE_GYRO_Z_VALUE_INDEX = 10
GYRO_UPDATE_ACCEL_X_VALUE_INDEX = 14
GYRO_UPDATE_ACCEL_Y_VALUE_INDEX = 18
GYRO_UPDATE_ACCEL_Z_VALUE_INDEX = 22
GYRO_UPDATE_MAG_X_VALUE_INDEX = 26
GYRO_UPDATE_MAG_Y_VALUE_INDEX = 30
GYRO_UPDATE_MAG_Z_VALUE_INDEX = 34
GYRO_UPDATE_TEMP_VALUE_INDEX = 38
GYRO_UPDATE_CHECKSUM_INDEX = 42
GYRO_UPDATE_TERMINATOR_INDEX = 44

@dataclass
class GyroUpdate:
    gyro_x: int
    gyro_y: int
    gyro_z: int
    accel_x: int
    accel_y: int
    accel_z: int
    mag_x: int
    mag_y: int
    mag_z: int
    temp_c: float

    def encode(self, protocol_buffer: bytes):
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = MSGID_GYRO_UPDATE

        # Data
        encodeProtocolUint16( self.gyro_x,           protocol_buffer, GYRO_UPDATE_GYRO_X_VALUE_INDEX )
        encodeProtocolUint16( self.gyro_y,           protocol_buffer, GYRO_UPDATE_GYRO_Y_VALUE_INDEX )
        encodeProtocolUint16( self.gyro_z,           protocol_buffer, GYRO_UPDATE_GYRO_Z_VALUE_INDEX )
        encodeProtocolUint16( self.accel_x,          protocol_buffer, GYRO_UPDATE_ACCEL_X_VALUE_INDEX )
        encodeProtocolUint16( self.accel_y,          protocol_buffer, GYRO_UPDATE_ACCEL_Y_VALUE_INDEX )
        encodeProtocolUint16( self.accel_z,          protocol_buffer, GYRO_UPDATE_ACCEL_Z_VALUE_INDEX )
        encodeProtocolUint16( np.uint16(self.mag_x), protocol_buffer, GYRO_UPDATE_MAG_X_VALUE_INDEX )
        encodeProtocolUint16( np.uint16(self.mag_y), protocol_buffer, GYRO_UPDATE_MAG_Y_VALUE_INDEX )
        encodeProtocolUint16( np.uint16(self.mag_z), protocol_buffer, GYRO_UPDATE_MAG_Z_VALUE_INDEX )
        encodeProtocolUnsignedHundredthsFloat(self.temp_c, protocol_buffer, GYRO_UPDATE_TEMP_VALUE_INDEX )

        # Footer
        encodeTermination( protocol_buffer, GYRO_UPDATE_MESSAGE_LENGTH, GYRO_UPDATE_MESSAGE_LENGTH - 4 )

        return GYRO_UPDATE_MESSAGE_LENGTH

    def decode(self, buffer: bytes) -> Optional[int]:
        if not verifyPrefix(buffer, GYRO_UPDATE_MESSAGE_LENGTH, [PACKET_START_CHAR, MSGID_GYRO_UPDATE], GYRO_UPDATE_CHECKSUM_INDEX):
            return None
        self.gyro_x  = decodeProtocolUint16( buffer, GYRO_UPDATE_GYRO_X_VALUE_INDEX )
        self.gyro_y  = decodeProtocolUint16( buffer, GYRO_UPDATE_GYRO_Y_VALUE_INDEX )
        self.gyro_z  = decodeProtocolUint16( buffer, GYRO_UPDATE_GYRO_Z_VALUE_INDEX )
        self.accel_x = decodeProtocolUint16( buffer, GYRO_UPDATE_ACCEL_X_VALUE_INDEX )
        self.accel_y = decodeProtocolUint16( buffer, GYRO_UPDATE_ACCEL_Y_VALUE_INDEX )
        self.accel_z = decodeProtocolUint16( buffer, GYRO_UPDATE_ACCEL_Z_VALUE_INDEX )
        self.mag_x   = np.int16_t(decodeProtocolUint16( buffer, GYRO_UPDATE_MAG_X_VALUE_INDEX ))
        self.mag_y   = np.int16_t(decodeProtocolUint16( buffer, GYRO_UPDATE_MAG_Y_VALUE_INDEX ))
        self.mag_z   = np.int16_t(decodeProtocolUint16( buffer, GYRO_UPDATE_MAG_Z_VALUE_INDEX ))
        self.temp_c  = decodeProtocolUnsignedHundredthsFloat(  buffer, GYRO_UPDATE_TEMP_VALUE_INDEX )
        return GYRO_UPDATE_MESSAGE_LENGTH



# Quaternion Update Packet - e.g., !r[q1][q2][q3][q4][accelx][accely][accelz][magx][magy][magz]

MSGID_QUATERNION_UPDATE = 'q'
QUATERNION_UPDATE_QUAT1_VALUE_INDEX = 2
QUATERNION_UPDATE_QUAT2_VALUE_INDEX = 6
QUATERNION_UPDATE_QUAT3_VALUE_INDEX = 10
QUATERNION_UPDATE_QUAT4_VALUE_INDEX = 14
QUATERNION_UPDATE_ACCEL_X_VALUE_INDEX = 18
QUATERNION_UPDATE_ACCEL_Y_VALUE_INDEX = 22
QUATERNION_UPDATE_ACCEL_Z_VALUE_INDEX = 26
QUATERNION_UPDATE_MAG_X_VALUE_INDEX = 30
QUATERNION_UPDATE_MAG_Y_VALUE_INDEX = 34
QUATERNION_UPDATE_MAG_Z_VALUE_INDEX = 38
QUATERNION_UPDATE_TEMP_VALUE_INDEX = 42
QUATERNION_UPDATE_CHECKSUM_INDEX = 49
QUATERNION_UPDATE_TERMINATOR_INDEX = 51
QUATERNION_UPDATE_MESSAGE_LENGTH = 53

@dataclass
class QuaternionUpdate:
    q1: int
    q2: int
    q3: int
    q4: int
    accel_x: int
    accel_y: int
    accel_z: int
    mag_x: int
    mag_y: int
    mag_z: int
    temp_c: float
    def encode(self, protocol_buffer: bytes) -> int:
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = MSGID_QUATERNION_UPDATE

        # Data
        encodeProtocolUint16(self.q1,               protocol_buffer, QUATERNION_UPDATE_QUAT1_VALUE_INDEX)
        encodeProtocolUint16(self.q2,               protocol_buffer, QUATERNION_UPDATE_QUAT2_VALUE_INDEX)
        encodeProtocolUint16(self.q3,               protocol_buffer, QUATERNION_UPDATE_QUAT3_VALUE_INDEX)
        encodeProtocolUint16(self.q4,               protocol_buffer, QUATERNION_UPDATE_QUAT4_VALUE_INDEX)
        encodeProtocolUint16(self.accel_x,          protocol_buffer, QUATERNION_UPDATE_ACCEL_X_VALUE_INDEX)
        encodeProtocolUint16(self.accel_y,          protocol_buffer, QUATERNION_UPDATE_ACCEL_Y_VALUE_INDEX)
        encodeProtocolUint16(self.accel_z,          protocol_buffer, QUATERNION_UPDATE_ACCEL_Z_VALUE_INDEX)
        encodeProtocolUint16(self.mag_x,            protocol_buffer, QUATERNION_UPDATE_MAG_X_VALUE_INDEX)
        encodeProtocolUint16(self.mag_y,            protocol_buffer, QUATERNION_UPDATE_MAG_Y_VALUE_INDEX)
        encodeProtocolUint16(self.mag_z,            protocol_buffer, QUATERNION_UPDATE_MAG_Z_VALUE_INDEX)
        encodeProtocolFloat( self.temp_c,           protocol_buffer, QUATERNION_UPDATE_TEMP_VALUE_INDEX)

        # Footer
        encodeTermination( protocol_buffer, QUATERNION_UPDATE_MESSAGE_LENGTH, QUATERNION_UPDATE_MESSAGE_LENGTH - 4 )

        return QUATERNION_UPDATE_MESSAGE_LENGTH

    def decode(self, buffer: bytes) -> Optional[int]:
        if not verifyPrefix(buffer, QUATERNION_UPDATE_MESSAGE_LENGTH, [PACKET_START_CHAR, MSGID_QUATERNION_UPDATE], QUATERNION_UPDATE_CHECKSUM_INDEX):
            return None
        self.q1      = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_QUAT1_VALUE_INDEX))
        self.q2      = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_QUAT2_VALUE_INDEX))
        self.q3      = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_QUAT3_VALUE_INDEX))
        self.q4      = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_QUAT4_VALUE_INDEX))
        self.accel_x = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_ACCEL_X_VALUE_INDEX))
        self.accel_y = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_ACCEL_Y_VALUE_INDEX))
        self.accel_z = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_ACCEL_Z_VALUE_INDEX))
        self.mag_x   = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_MAG_X_VALUE_INDEX))
        self.mag_y   = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_MAG_Y_VALUE_INDEX))
        self.mag_z   = np.int16(decodeProtocolUint16(buffer, QUATERNION_UPDATE_MAG_Z_VALUE_INDEX))
        self.temp_c  = decodeProtocolFloat(buffer, QUATERNION_UPDATE_TEMP_VALUE_INDEX)
        return QUATERNION_UPDATE_MESSAGE_LENGTH



# EnableStream Response Packet - e.g., !s[stream type][gyro full scale range][accel full scale range][update rate hz][yaw_offset_degrees][q1/2/3/4 offsets][flags][checksum][cr][lf]
MSG_ID_STREAM_RESPONSE = 's'
STREAM_RESPONSE_STREAM_TYPE_INDEX = 2
STREAM_RESPONSE_GYRO_FULL_SCALE_DPS_RANGE = 3
STREAM_RESPONSE_ACCEL_FULL_SCALE_G_RANGE = 7
STREAM_RESPONSE_UPDATE_RATE_HZ = 11
STREAM_RESPONSE_YAW_OFFSET_DEGREES = 15
STREAM_RESPONSE_QUAT1_OFFSET = 22 #  Deprecated 
STREAM_RESPONSE_QUAT2_OFFSET = 26 #  Deprecated 
STREAM_RESPONSE_QUAT3_OFFSET = 30 #  Deprecated 
STREAM_RESPONSE_QUAT4_OFFSET = 34 #  Deprecated 
STREAM_RESPONSE_FLAGS = 38
STREAM_RESPONSE_CHECKSUM_INDEX = 42
STREAM_RESPONSE_TERMINATOR_INDEX = 44
STREAM_RESPONSE_MESSAGE_LENGTH = 46

@dataclass
class StreamResponse:
    stream_type: int = 0
    gyro_fsr_dps: int = 0
    accel_fsr_g: int = 0
    update_rate_hz: int = 0
    yaw_offset_degrees: float = 0.0
    q1_offset: int = 0
    q2_offset: int = 0
    q3_offset: int = 0
    q4_offset: int = 0
    flags: int = 0

    def encode(self, protocol_buffer: bytes) -> int:
        # Header
        protocol_buffer[0] = PACKET_START_CHAR
        protocol_buffer[1] = MSG_ID_STREAM_RESPONSE

        # Data
        protocol_buffer[STREAM_RESPONSE_STREAM_TYPE_INDEX] = self.stream_type
        encodeProtocolUint16(  self.gyro_fsr_dps,        protocol_buffer, STREAM_RESPONSE_GYRO_FULL_SCALE_DPS_RANGE)
        encodeProtocolUint16(  self.accel_fsr_g,         protocol_buffer, STREAM_RESPONSE_ACCEL_FULL_SCALE_G_RANGE)
        encodeProtocolUint16(  self.update_rate_hz,      protocol_buffer, STREAM_RESPONSE_UPDATE_RATE_HZ)
        encodeProtocolFloat(   self.yaw_offset_degrees,  protocol_buffer, STREAM_RESPONSE_YAW_OFFSET_DEGREES)
        encodeProtocolUint16(  self.q1_offset,           protocol_buffer, STREAM_RESPONSE_QUAT1_OFFSET)
        encodeProtocolUint16(  self.q2_offset,           protocol_buffer, STREAM_RESPONSE_QUAT2_OFFSET)
        encodeProtocolUint16(  self.q3_offset,           protocol_buffer, STREAM_RESPONSE_QUAT3_OFFSET)
        encodeProtocolUint16(  self.q4_offset,           protocol_buffer, STREAM_RESPONSE_QUAT4_OFFSET)
        encodeProtocolUint16(  self.flags,               protocol_buffer, STREAM_RESPONSE_FLAGS)

        # Footer
        encodeTermination( protocol_buffer, STREAM_RESPONSE_MESSAGE_LENGTH, STREAM_RESPONSE_MESSAGE_LENGTH - 4 )

        return STREAM_RESPONSE_MESSAGE_LENGTH

    def decode(self, buffer: bytes) -> Optional[int]:
        if not verifyPrefix(buffer, STREAM_RESPONSE_MESSAGE_LENGTH, [PACKET_START_CHAR, MSG_ID_STREAM_RESPONSE], STREAM_RESPONSE_CHECKSUM_INDEX):
            return None
        self.stream_type         = buffer[2]
        self.gyro_fsr_dps        = decodeProtocolUint16(buffer, STREAM_RESPONSE_GYRO_FULL_SCALE_DPS_RANGE)
        self.accel_fsr_g         = decodeProtocolUint16(buffer, STREAM_RESPONSE_ACCEL_FULL_SCALE_G_RANGE)
        self.update_rate_hz      = decodeProtocolUint16(buffer, STREAM_RESPONSE_UPDATE_RATE_HZ)
        self.yaw_offset_degrees  = decodeProtocolFloat( buffer, STREAM_RESPONSE_YAW_OFFSET_DEGREES)
        self.q1_offset           = decodeProtocolUint16(buffer, STREAM_RESPONSE_QUAT1_OFFSET)
        self.q2_offset           = decodeProtocolUint16(buffer, STREAM_RESPONSE_QUAT2_OFFSET)
        self.q3_offset           = decodeProtocolUint16(buffer, STREAM_RESPONSE_QUAT3_OFFSET)
        self.q4_offset           = decodeProtocolUint16(buffer, STREAM_RESPONSE_QUAT4_OFFSET)
        self.flags               = decodeProtocolUint16(buffer, STREAM_RESPONSE_FLAGS)
        return STREAM_RESPONSE_MESSAGE_LENGTH


# EnableStream Command Packet - e.g., !S[stream type]

MSGID_STREAM_CMD = 'S'
STREAM_CMD_STREAM_TYPE_YPR = MSGID_YPR_UPDATE
STREAM_CMD_STREAM_TYPE_QUATERNION = MSGID_QUATERNION_UPDATE
STREAM_CMD_STREAM_TYPE_RAW = MSGID_RAW_UPDATE
STREAM_CMD_STREAM_TYPE_INDEX = 2
STREAM_CMD_UPDATE_RATE_HZ_INDEX = 3
STREAM_CMD_CHECKSUM_INDEX = 5
STREAM_CMD_TERMINATOR_INDEX = 7
STREAM_CMD_MESSAGE_LENGTH = 9

def encodeStreamCommand(protocol_buffer: bytes, stream_type: np.int8, update_rate_hz: np.uint8) -> int:
    # Header
    protocol_buffer[0] = PACKET_START_CHAR
    protocol_buffer[1] = MSGID_STREAM_CMD

    # Data
    protocol_buffer[STREAM_CMD_STREAM_TYPE_INDEX] = stream_type
    # convert update_rate_hz to two ascii bytes
    protocol_buffer[STREAM_CMD_UPDATE_RATE_HZ_INDEX:STREAM_CMD_UPDATE_RATE_HZ_INDEX+2] = bytes(f"{update_rate_hz:#02}", 'ascii')

    # Footer
    encodeTermination( protocol_buffer, STREAM_CMD_MESSAGE_LENGTH, STREAM_CMD_MESSAGE_LENGTH - 4 )

    return STREAM_CMD_MESSAGE_LENGTH

# def decodeStreamCommand(buffer: bytes, char& stream_type, unsigned char& update_rate_hz ) -> Optional[int]:
#     if ( length < STREAM_CMD_MESSAGE_LENGTH ) return 0
#     if ( ( buffer[0] == '!' ) && ( buffer[1] == MSGID_STREAM_CMD ) )
#     {
#         if ( !verifyChecksum( buffer, STREAM_CMD_CHECKSUM_INDEX ) ) return 0

#         stream_type = buffer[STREAM_CMD_STREAM_TYPE_INDEX]
#         update_rate_hz = decodeUint8( buffer, STREAM_CMD_UPDATE_RATE_HZ_INDEX )

#         return STREAM_CMD_MESSAGE_LENGTH
#     }
#     return 0
# }


IMU_PROTOCOL_MAX_MESSAGE_LENGTH = QUATERNION_UPDATE_MESSAGE_LENGTH