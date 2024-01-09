import numpy as np
from callbacks import IIOProvider, IIOCompleteNotification, IBoardCapabilities, BoardState
from imu_protocol import (
    StreamResponse,
    YPRUpdate,
    GyroUpdate,
    PACKET_START_CHAR,
    MSGID_GYRO_UPDATE,
    NAV6_FLAG_MASK_CALIBRATION_STATE,
    IMU_PROTOCOL_MAX_MESSAGE_LENGTH,
)
from serial import Serial
from ahrs_protocol import (
    IntegrationControl, BoardID,
    AHRSUpdate, AHRSPosUpdate, AHRSPosTSUpdate,
    BINARY_PACKET_INDICATOR_CHAR,
    MSGID_AHRSPOS_TS_UPDATE,
    MSGID_AHRSPOS_UPDATE,
    MSGID_AHRS_UPDATE,
    AHRS_DATA_TYPE,
    AHRS_TUNING_VAR_ID,
)
from imu_registers import (
    NAVX_INTEGRATION_CTL_RESET_DISP_X,
    NAVX_INTEGRATION_CTL_RESET_YAW,
    NAVX_INTEGRATION_CTL_RESET_DISP_Y,
    NAVX_INTEGRATION_CTL_RESET_DISP_Z,
)
import imu_protocol
import ahrs_protocol
import time

IO_TIMEOUT_SECONDS = 1.0

class SerialIO(IIOProvider):
    def __init__(self, port_id: str, update_rate_hz: int, processed_data: bool, notify_sink: IIOCompleteNotification, board_capabilities: IBoardCapabilities) -> None:
        super().__init__()
        self.serial_port_id = port_id
        self.ypr_update_data = YPRUpdate()
        self.gyro_update_data = GyroUpdate()
        self.ahrs_update_data = AHRSUpdate()
        self.ahrspos_update_data = AHRSPosUpdate()
        self.ahrspos_ts_update_data = AHRSPosTSUpdate()
        self.board_id = BoardID(0, 0, 0, 0, 0, [0] * 12)
        self.board_state = BoardState(0, 0, 0, 0, 0, 0, 0, 0)
        self.notify_sink = notify_sink
        self.board_capabilities = board_capabilities
        self._serial_port = None
        self._serial_port = self.GetMaybeCreateSerialPort()
        self.update_rate_hz = update_rate_hz
        if processed_data:
            self.update_type = MSGID_AHRSPOS_TS_UPDATE
        else:
            self.update_type = MSGID_GYRO_UPDATE
        
        self._stop = False
        self.byte_count = 0
    
    def reset_serial_port(self):
        if (self._serial_port is not None):
            self._serial_port.close()
            self._serial_port = None
        self.GetMaybeCreateSerialPort()
        return self._serial_port

    def GetMaybeCreateSerialPort(self):
        if self._serial_port is not None:
            return self._serial_port
        
        try:
            self._serial_port = Serial(
                self.serial_port_id, 57600,
                timeout=1.0
            )
            self._serial_port.reset_input_buffer()
            self._serial_port.reset_output_buffer()
            # self._serial_port.SetReadBufferSize(256)
            # self._serial_port.EnableTermination('\n')
            # self._serial_port.Reset()
        except Exception as e:
            print("ERROR Opening Serial Port!\n")
            self._serial_port = None
    
    def EnqueueIntegrationControlMessage(self, action: int):
        self.next_integration_control_action = action
        self.signal_transmit_integration_control = True

    def DispatchStreamResponse(self, response: StreamResponse):
        self.board_state.cal_status = np.uint8(response.flags & NAV6_FLAG_MASK_CALIBRATION_STATE)
        self.board_state.capability_flags = np.int16(response.flags & ~NAV6_FLAG_MASK_CALIBRATION_STATE)
        self.board_state.op_status = 0x04 # TODO:  Create a symbol for this
        self.board_state.selftest_status = 0x07 # TODO:  Create a symbol for this
        self.board_state.accel_fsr_g = response.accel_fsr_g
        self.board_state.gyro_fsr_dps = response.gyro_fsr_dps
        self.board_state.update_rate_hz = np.uint8(response.update_rate_hz)
        self.notify_sink.set_BoardState(self.board_state)
        # If AHRSPOS_TS is update type is requested, but board doesn't support it,
        # retransmit the stream config, falling back to AHRSPos update mode, if   
        # the board supports it, otherwise fall all the way back to AHRS Update mode.
        if self.update_type == MSGID_AHRSPOS_TS_UPDATE:
            if self.board_capabilities.is_AHRSPosTimestamp_supported():
                self.update_type = MSGID_AHRSPOS_TS_UPDATE
            elif self.board_capabilities.is_displacement_supported():
                self.update_type = MSGID_AHRSPOS_UPDATE
            else:
                self.update_type = MSGID_AHRS_UPDATE
            self.signal_retransmit_stream_config = True

    def DecodePacketHandler(self, received_data: bytes):
        sensor_timestamp = 0 # Serial protocols do not provide sensor timestamps.

        if (packet_length := self.ypr_update_data.decode(received_data)) is not None:
            self.notify_sink.set_ypr(self.ypr_update_data, sensor_timestamp)
            #printf("UPDATING YPR Data\n")
        elif (packet_length := self.ahrspos_ts_update_data.decode(received_data)) is not None:
            self.notify_sink.set_AHRSPosData(self.ahrspos_ts_update_data, self.ahrspos_ts_update_data.timestamp)
            #printf("UPDATING AHRSPosTS Data\n")
        elif ( packet_length := self.ahrspos_update_data.decode(received_data)) is not None:
            self.notify_sink.set_AHRSPosData(self.ahrspos_update_data, sensor_timestamp)
            #printf("UPDATING AHRSPos Data\n")
        elif ( packet_length := self.ahrs_update_data.decode(received_data)) is not None:
            self.notify_sink.set_AHRSData(self.ahrs_update_data, sensor_timestamp)
            #printf("UPDATING AHRS Data\n")
        elif ( packet_length := self.gyro_update_data.decode(received_data)) is not None:
            self.notify_sink.set_raw_data(self.gyro_update_data, sensor_timestamp)
            #printf("UPDAING GYRO Data\n")
        elif ( packet_length := self.board_id.decode(received_data)) is not None:
            self.notify_sink.set_board_id(self.board_id)
            #printf("UPDATING ELSE\n")
        else:
            packet_length = 0
        return packet_length

    def run(self):
        if self._serial_port is None:
            return
        self._stop = False
        stream_response_received = False
        last_stream_command_sent_timestamp = 0.0
        last_data_received_timestamp = 0.0
        last_second_start_time = 0.0

        partial_binary_packet_count = 0
        stream_response_receive_count = 0
        timeout_count = 0
        discarded_bytes_count = 0
        port_reset_count = 0
        updates_in_last_second = 0
        integration_response_receive_count = 0

        try:
            self.serial_port.SetReadBufferSize(256)
            self.serial_port.SetTimeout(1.0)
            self.serial_port.EnableTermination('\n')
            self.serial_port.Flush()
            self.serial_port.Reset()
        except Exception as e:
            print("SerialPort Run() Port Initialization Exception:  %s\n", e)

        stream_command = bytearray(256)
        integration_control_command = bytearray(256)
        response = StreamResponse()
        integration_control = IntegrationControl(0, 0)
        integration_control_response = IntegrationControl(0, 0)

        cmd_packet_length = imu_protocol.encodeStreamCommand(stream_command, self.update_type, self.update_rate_hz )
        try:
            self._serial_port.Reset()
            #std::cout << "Initial Write" << std::endl
            self._serial_port.Write( stream_command, cmd_packet_length)
            cmd_packet_length = ahrs_protocol.encodeDataGetRequest( stream_command,  AHRS_DATA_TYPE.BOARD_IDENTITY, AHRS_TUNING_VAR_ID.UNSPECIFIED)
            self._serial_port.Write( stream_command, cmd_packet_length )
            self._serial_port.Flush()
            port_reset_count += 1
            last_stream_command_sent_timestamp = time(0)
        except Exception as e:
            print("SerialPort Run() Port Send Encode Stream Command Exception:  %s\n", e)


        remainder_bytes = 0
        received_data = bytearray(256 * 3)
        additional_received_data = bytearray(256)
        remainder_data = bytearray(256)

        updater = 0
        while not self._stop:
            try:
                if updater == 100:
                    cmd_packet_length = imu_protocol.encodeStreamCommand( stream_command, self.update_type, self.update_rate_hz )
                    self._serial_port.write(stream_command[:cmd_packet_length])
                    updater = 0
                updater += 1

                # Wait, with delays to conserve CPU resources, until
                # bytes have arrived.

                if ( signal_transmit_integration_control ):
                    integration_control.action = next_integration_control_action
                    signal_transmit_integration_control = False
                    next_integration_control_action = 0
                    cmd_packet_length = integration_control.encode(integration_control_command)
                    try:
                        #std::cout << "No idea where this write is..." << std::endl
                        #DEBUG-TODO: Determine if this is needed
                        #serial_port.Write( integration_control_command, cmd_packet_length )
                        pass
                    except Exception as e:
                        print("SerialPort Run() IntegrationControl Send Exception:  %s\n", e)


                if (not self._stop) and ( remainder_bytes == 0 ) and ( self._serial_port.in_waiting < 1 ):
                    #usleep(1000000/update_rate_hz)
                    self._serial_port.WaitForData()

                packets_received = 0
                bytes_read = self._serial_port.readinto(received_data)
                byte_count += bytes_read

                # If a partial packet remains from last iteration, place that at
                # the start of the data buffer, and append any new data available
                # at the serial port.

                if ( remainder_bytes > 0 ):
                    memcpy( received_data + bytes_read, remainder_data, remainder_bytes)
                    bytes_read += remainder_bytes
                    remainder_bytes = 0

                if (bytes_read > 0):
                    last_data_received_timestamp = time.time()
                    i = 0
                    # Scan the buffer looking for valid packets
                    while (i < bytes_read):
                        # Attempt to decode a packet
                        bytes_remaining = bytes_read - i

                        if received_data[i] != PACKET_START_CHAR:
                            # Skip over received bytes until a packet start is detected.
                            i += 1
                            discarded_bytes_count += 1
                            continue
                        else:
                            if ( ( bytes_remaining > 2 ) and ( received_data[i+1] == BINARY_PACKET_INDICATOR_CHAR ) ):
                                # Binary packet received next byte is packet length-2
                                total_expected_binary_data_bytes = received_data[i+2]
                                total_expected_binary_data_bytes += 2
                                while ( bytes_remaining < total_expected_binary_data_bytes ):

                                    # This binary packet contains an embedded
                                    # end-of-line character.  Continue to receive
                                    # more data until entire packet is received.
                                    additional_received_data_length = self._serial_port.readinto(additional_received_data)
                                    self.byte_count += additional_received_data_length

                                    # Resize array to hold existing and new data
                                    if additional_received_data_length > 0:
                                        memcpy( received_data + bytes_remaining, additional_received_data, additional_received_data_length)
                                        bytes_remaining += additional_received_data_length
                                    else:
                                        # Timeout waiting for remainder of binary packet */
                                        i += 1
                                        bytes_remaining -= 1
                                        partial_binary_packet_count += 1
                                        continue

                        packet_length = self.DecodePacketHandler(received_data + i,bytes_remaining)
                        if (packet_length > 0):
                            packets_received += 1
                            update_count += 1
                            self.last_valid_packet_time = time.time()
                            updates_in_last_second += 1
                            if ((self.last_valid_packet_time - last_second_start_time ) > 1.0 ):
                                updates_in_last_second = 0
                                last_second_start_time = self.last_valid_packet_time
                            i += packet_length
                        else:
                            packet_length = imu_protocol.decodeStreamResponse(received_data + i, bytes_remaining, response)
                            if (packet_length > 0):
                                packets_received += 1
                                self.DispatchStreamResponse(response)
                                stream_response_received = True
                                i += packet_length
                                stream_response_receive_count += 1
                            else:
                                packet_length = ahrs_protocol.decodeIntegrationControlResponse( received_data + i, bytes_remaining,
                                        integration_control_response )
                                if ( packet_length > 0 ):
                                    # Confirmation of integration control
                                    integration_response_receive_count += 1
                                    i += packet_length
                                else:
                                    # Even though a start-of-packet indicator was found, the 
                                    # current index is not the start of a packet if interest.
                                    # Scan to the beginning of the next packet,              
                                    next_packet_start_found = False
                                    x = 0
                                    while x < bytes_remaining:
                                        if ( received_data[i + x] != PACKET_START_CHAR):
                                            x += 2
                                        else:
                                            i += x
                                            bytes_remaining -= x
                                            if ( x != 0 ):
                                                next_packet_start_found = True
                                            break
                                    discard_remainder = False
                                    if ( not next_packet_start_found and x == bytes_remaining ):
                                        # Remaining bytes don't include a start-of-packet
                                        discard_remainder = True
                                    partial_packet = False
                                    if ( discard_remainder ):
                                        # Discard the remainder
                                        i = bytes_remaining
                                    else:
                                        if (not next_packet_start_found ):
                                            # This occurs when packets are received that are not decoded.  
                                            # Bump over this packet and prepare for the next.              
                                            if ( ( bytes_remaining > 2 ) and ( received_data[i+1] == BINARY_PACKET_INDICATOR_CHAR ) ):
                                                # Binary packet received next byte is packet length-2
                                                pkt_len = received_data[i+2]
                                                pkt_len += 2
                                                if ( bytes_remaining >= pkt_len ):
                                                    bytes_remaining -= pkt_len
                                                    i += pkt_len
                                                    discarded_bytes_count += pkt_len
                                                else:
                                                    # This is the initial portion of a partial binary packet.
                                                    # Keep this data and attempt to acquire the remainder.   
                                                    partial_packet = True
                                            else:
                                                # Ascii packet received.
                                                # Scan up to and including next end-of-packet character
                                                # sequence, or the beginning of a new packet.
                                                x = 0
                                                while x < bytes_remaining, x++:
                                                    if (received_data[i+x] == '\r'):
                                                        i += x+1
                                                        bytes_remaining -= (x+1)
                                                        discarded_bytes_count += x+1
                                                        if ( ( bytes_remaining > 0 ) and  received_data[i] == '\n'):
                                                            bytes_remaining -= 1
                                                            i += 1
                                                            discarded_bytes_count += 1
                                                        break
                                                    # If a new start-of-packet is found, discard
                                                    # the ascii packet bytes that precede it.   
                                                    if ( received_data[i+x] == '!'):
                                                        if ( x > 0 ):
                                                            i += x
                                                            bytes_remaining -= x
                                                            discarded_bytes_count += x
                                                            break
                                                        else:
                                                            # start of packet found, but no termination    
                                                            # Time to get some more data, unless the bytes 
                                                            # remaining are larger than a valid packet size
                                                            if ( bytes_remaining < IMU_PROTOCOL_MAX_MESSAGE_LENGTH ):
                                                                # Get more data
                                                                partial_packet = True
                                                            else:
                                                                i += 1
                                                                bytes_remaining -= 1
                                                            break
                                                if ( x == bytes_remaining ):
                                                    # Partial ascii packet - keep the remainder
                                                    partial_packet = True
                                    if partial_packet:
                                        if bytes_remaining > len(remainder_data):
                                            remainder_data[:] = received_data[i - ]
                                            memcpy(remainder_data, received_data + i - sizeof(remainder_data), sizeof(remainder_data))
                                            remainder_bytes = sizeof(remainder_data)
                                        else:
                                            remainder_data[:bytes_remaining] = received_data[i:i+bytes_remaining]
                                            remainder_bytes = bytes_remaining
                                        i = bytes_read

                    if ( ( packets_received == 0 ) and ( bytes_read == 256 ) ):
                        # Workaround for issue found in SerialPort implementation:
                        # No packets received and 256 bytes received this
                        # condition occurs in the SerialPort.  In this case,
                        # reset the serial port.
                        self._serial_port.flush()
                        self._serial_port.reset_input_buffer()
                        port_reset_count += 1

                    retransmit_stream_config = False
                    if ( signal_retransmit_stream_config ):
                        retransmit_stream_config = True
                        signal_retransmit_stream_config = False

                    # If a stream configuration response has not been received within three seconds
                    # of operation, (re)send a stream configuration request

                    #std::cout << "Config: " << retransmit_stream_config << " Time: " << (time(0) - last_stream_command_sent_timestamp ) << " " << last_stream_command_sent_timestamp << std::endl
            
                    #DEBUG-TODO: Enable this if we really need it
                    if (False and (retransmit_stream_config or ((not stream_response_received) and ((time(0) - last_stream_command_sent_timestamp ) > 3.0 ) ) ) ):
                        cmd_packet_length = imu_protocol.encodeStreamCommand( stream_command, update_type, update_rate_hz )
                        try:
                            ResetSerialPort()
                            last_stream_command_sent_timestamp = time(0)
                            #std::cout << "Retransmitting Stream Command!!!!" << std::endl
                            serial_port.Write( stream_command, cmd_packet_length )
                            cmd_packet_length = ahrs_protocol.encodeDataGetRequest( stream_command,  AHRS_DATA_TYPE.BOARD_IDENTITY, AHRS_TUNING_VAR_ID.UNSPECIFIED )
                            serial_port.Write( stream_command, cmd_packet_length )
                            serial_port.Flush()
                        except Exception as ex2:
                            print("SerialPort Run() Re-transmit Encode Stream Command Exception:  %s\n", ex2.what())
                    else:
                        # If no bytes remain in the buffer, and not awaiting a response, sleep a bit
                        if ( stream_response_received and ( self._serial_port.GetBytesReceived() == 0 ) ):
                            self._serial_port.WaitForData()

                    # If receiving data, but no valid packets have been received in the last second
                    # the navX MXP may have been reset, but no exception has been detected.        
                    # In this case , trigger transmission of a new stream_command, to ensure the   
                    # streaming packet type is configured correctly.                               

                    if (time.time() - self.last_valid_packet_time) > 1.0:
                        last_stream_command_sent_timestamp = time(0)
                        stream_response_received = False
                else:
                    # No data received this time around
                    if time.time() - last_data_received_timestamp > 1.0:
                        self.reset_serial_port()
            except Exception as e:
                # This exception typically indicates a Timeout, but can also be a buffer overrun error.
                stream_response_received = False
                timeout_count += 1
                self.reset_serial_port()

        self._serial_port.close()
            
    def is_connected(self):
        time_since_last_update = time.time() - self.last_valid_packet_time
        return time_since_last_update <= IO_TIMEOUT_SECONDS

    def get_byte_count(self) -> float:
        return self.byte_count
    def get_update_count(self) -> float:
        return self.update_count
    def set_update_rate_hz(self, update_rate: int):
        self.update_rate_hz = update_rate
    def zero_yaw(self):
        self.EnqueueIntegrationControlMessage(NAVX_INTEGRATION_CTL_RESET_YAW)
    def zero_displacement(self):
        self.EnqueueIntegrationControlMessage( NAVX_INTEGRATION_CTL_RESET_DISP_X |
                                        NAVX_INTEGRATION_CTL_RESET_DISP_Y |
                                        NAVX_INTEGRATION_CTL_RESET_DISP_Z )

    def stop(self):
        self._stop = True