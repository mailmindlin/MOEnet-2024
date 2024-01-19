package frc.robot.sensor.imu;

import edu.wpi.first.math.geometry.Rotation2d;
import edu.wpi.first.math.geometry.Rotation3d;

public interface Gyro3d {
    Rotation3d getRotation3d();
    default Rotation2d getRotation2d() {
        return getRotation3d().toRotation2d();
    }
}
