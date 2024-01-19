package frc.robot.sensor.vision.io;

import java.nio.ByteBuffer;
import java.time.Instant;

import edu.wpi.first.math.Matrix;
import edu.wpi.first.math.geometry.Pose3d;
import edu.wpi.first.math.geometry.Twist3d;
import edu.wpi.first.math.numbers.N6;
import edu.wpi.first.util.struct.Struct;
import edu.wpi.first.util.struct.StructSerializable;
import frc.robot.sensor.time.HasTimestamp;

public class PositionEstimate implements StructSerializable, HasTimestamp {
    public static final Struct<PositionEstimate> struct = new RobotPositionStruct();

    private final Instant timestamp;
    private final Pose3d pose;
    private final Matrix<N6, N6> poseCovariance;
    private final Twist3d twist;
    private final Matrix<N6, N6> twistCovariance;
    
    public PositionEstimate(Instant timestamp, Pose3d pose, Matrix<N6, N6> poseCovariance, Twist3d twist, Matrix<N6, N6> twistCovariance) {
        this.timestamp = timestamp;
        this.pose = pose;
        this.poseCovariance = poseCovariance;
        this.twist = twist;
        this.twistCovariance = twistCovariance;
    }

    @Override
    public Instant getTimestamp() {
        return this.timestamp;
    }

    public Pose3d getPose() {
        return pose;
    }

    public Matrix<N6, N6> getPoseCovariance() {
        return poseCovariance;
    }

    public Twist3d getTwist() {
        return twist;
    }

    public Matrix<N6, N6> getTwistCovariance() {
        return twistCovariance;
    }

    static final class RobotPositionStruct implements Struct<PositionEstimate> {
        @Override
        public Class<PositionEstimate> getTypeClass() {
            return PositionEstimate.class;
        }

        @Override
        public String getTypeString() {
            return "struct:PositionEstimate";
        }

        @Override
        public int getSize() {
            return Pose3d.struct.getSize() + (Mat66Struct.struct.getSize() * 2) + Twist3d.struct.getSize();
        }

        @Override
        public String getSchema() {
            return "Instant ts;Pose3d pose;Mat66 poseCov;Twist3d twist;Mat66 twistCov";
        }

        @Override
        public PositionEstimate unpack(ByteBuffer bb) {
            var timestamp = InstantStruct.struct.unpack(bb);
            var pose = Pose3d.struct.unpack(bb);
            var poseCov = Mat66Struct.struct.unpack(bb);
            var twist = Twist3d.struct.unpack(bb);
            var twistCov = Mat66Struct.struct.unpack(bb);
            return new PositionEstimate(timestamp, pose, poseCov, twist, twistCov);
        }

        @Override
        public void pack(ByteBuffer bb, PositionEstimate value) {
            InstantStruct.struct.pack(bb, value.timestamp);
            Pose3d.struct.pack(bb, value.pose);
            Mat66Struct.struct.pack(bb, value.poseCovariance);
            Twist3d.struct.pack(bb, value.twist);
            Mat66Struct.struct.pack(bb, value.twistCovariance);
        }
    }
}
