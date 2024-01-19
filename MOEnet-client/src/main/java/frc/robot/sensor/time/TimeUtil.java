package frc.robot.sensor.time;

import java.time.Instant;

public final class TimeUtil {
    private TimeUtil() {}

    public static Instant fromMicros(long micros) {
        return Instant.ofEpochSecond(micros / 1_000_000, (micros % 1_000_000) * 1_000);
    }
}
