package frc.robot.sensor.vision.io;

import edu.wpi.first.util.protobuf.Protobuf;
import us.hebi.quickbuf.ProtoMessage;

public interface ProtobufPlus<T, MessageType extends ProtoMessage<?>> extends Protobuf<T, MessageType> {
    default MessageType pack(T value) {
        var msg = this.createMessage();
        this.pack(msg, value);
        return msg;
    }
}
