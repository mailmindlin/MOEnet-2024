package frc.robot.sensor.vision.io;

import java.time.Instant;

import com.mindlin.moenet.proto.Timestamp;

import us.hebi.quickbuf.Descriptors.Descriptor;

public class InstantProto implements ProtobufPlus<Instant, Timestamp> {
    public static final InstantProto proto = new InstantProto();
    @Override
    public Class<Instant> getTypeClass() {
        return Instant.class;
    }

    @Override
    public Descriptor getDescriptor() {
        return Timestamp.getDescriptor();
    }

    @Override
    public Timestamp createMessage() {
        return Timestamp.newInstance();
    }

    @Override
    public Instant unpack(Timestamp msg) {
        return Instant.ofEpochSecond(msg.getSeconds(), msg.getNanos());
    }

    @Override
    public void pack(Timestamp msg, Instant value) {
        msg.setSeconds(value.getEpochSecond());
        msg.setNanos(value.getNano());
    }
}
