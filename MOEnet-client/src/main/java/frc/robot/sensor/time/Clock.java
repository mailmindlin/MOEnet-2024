package frc.robot.sensor.time;

public interface Clock<C extends Clock<C>> {
    Timestamp<C> now();
}
