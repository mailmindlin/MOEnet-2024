package frc.robot.sensor.vision;

import edu.wpi.first.math.geometry.CoordinateSystem;
import edu.wpi.first.math.geometry.Rotation3d;

public interface OrientationSensor {
    CoordinateSystem getCoordinateSystem();
    Rotation3d getOrientation();
}
