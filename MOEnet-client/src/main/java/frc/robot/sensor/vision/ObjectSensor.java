package frc.robot.sensor.vision;

import frc.robot.sensor.vision.io.ObjectDetection;

public interface ObjectSensor {
    Iterable<ObjectDetection> getDetections();
}
