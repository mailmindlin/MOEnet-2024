package frc.robot.sensor.vision.io;

import edu.wpi.first.math.geometry.Translation3d;
import us.hebi.quickbuf.Descriptors.Descriptor;

public class Translation3dProto implements ProtobufPlus<Translation3d, com.mindlin.moenet.proto.Translation3d> {
    public static final Translation3dProto INSTANCE = new Translation3dProto();

    @Override
    public Class<Translation3d> getTypeClass() {
        return Translation3d.class;
    }

    @Override
    public Descriptor getDescriptor() {
        return com.mindlin.moenet.proto.Translation3d.getDescriptor();
    }

    @Override
    public com.mindlin.moenet.proto.Translation3d createMessage() {
        return com.mindlin.moenet.proto.Translation3d.newInstance();
    }

    @Override
    public Translation3d unpack(com.mindlin.moenet.proto.Translation3d msg) {
        return new Translation3d(msg.getX(), msg.getY(), msg.getZ());
    }

    @Override
    public void pack(com.mindlin.moenet.proto.Translation3d msg, Translation3d value) {
        msg.setX(value.getX());
        msg.setY(value.getY());
        msg.setZ(value.getZ());
    }
}
