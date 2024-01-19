package frc.robot.sensor.time;

import java.time.Instant;

public final class Timestamped<V> implements HasTimestamp {
    private final Instant timestamp;
    private final V value;
    public Timestamped(Instant timestamp, V value) {
        this.timestamp = timestamp;
        this.value = value;
    }
    
    @Override
    public Instant getTimestamp() {
        return timestamp;
    }

    public V getValue() {
        return value;
    }
}
