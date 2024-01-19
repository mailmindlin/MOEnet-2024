package frc.robot.sensor.vision;

import edu.wpi.first.math.geometry.Pose2d;
import edu.wpi.first.math.geometry.Pose3d;

public interface PoseSensor {
    Pose3d getPose3d();
    default Pose2d getPose2d() {
        return getPose3d().toPose2d();
    }
    boolean isRelative();
}
