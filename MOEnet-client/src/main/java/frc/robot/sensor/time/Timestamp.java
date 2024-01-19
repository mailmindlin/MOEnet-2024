package frc.robot.sensor.time;

import java.util.Objects;

public class Timestamp<C extends Clock<C>> {
    private final C clock;
    private final long seconds;
    private final int nanos;

    public static <C extends Clock<C>> Timestamp<C> now(C clock) {
        return clock.now();
    }

    Timestamp(C clock, long seconds, int nanos) {
        this.clock = Objects.requireNonNull(clock, "clock");
        this.seconds = seconds;
        if (nanos < 0)
            throw new IllegalArgumentException("Negative nanoseconds part");
        this.nanos = nanos;
    }

    public C getClock() {
        return this.clock;
    }

    public long getSeconds() {
        return this.seconds;
    }

    public int getNanos() {
        return this.nanos;
    }
}
