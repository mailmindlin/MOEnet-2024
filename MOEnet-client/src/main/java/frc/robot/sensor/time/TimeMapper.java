package frc.robot.sensor.time;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public interface TimeMapper<Ca extends Clock<Ca>, Cb extends Clock<Cb>> {
    Ca getClockA();
    Cb getClockB();

    Timestamp<Cb> convertAtoB(Timestamp<Ca> timestampA);
    Timestamp<Ca> convertBtoA(Timestamp<Cb> timestampB);

    default <Cc extends Clock<Cc>> TimeMapper<Ca, Cc> chain(TimeMapper<Cb, Cc> next) {
        Objects.requireNonNull(next, "next");
        return new ChainTimeMapper<>(List.of(this, next));
    }

    /**
     * Get a TimeMapper that applies the inverse transform
     * @return
     */
    default TimeMapper<Cb, Ca> invert() {
        return new InverseTimeMapper<>(this);
    }

    static final class InverseTimeMapper<Ca extends Clock<Ca>, Cb extends Clock<Cb>> implements TimeMapper<Ca, Cb> {
        private final TimeMapper<Cb, Ca> source;
        InverseTimeMapper(TimeMapper<Cb, Ca> source) {
            this.source = Objects.requireNonNull(source);
        }
        @Override
        public Ca getClockA() {
            return source.getClockB();
        }
        @Override
        public Cb getClockB() {
            return source.getClockA();
        }
        @Override
        public Timestamp<Cb> convertAtoB(Timestamp<Ca> timestampA) {
            return source.convertBtoA(timestampA);
        }
        @Override
        public Timestamp<Ca> convertBtoA(Timestamp<Cb> timestampB) {
            return source.convertAtoB(timestampB);
        }
        
        @Override
        public TimeMapper<Cb, Ca> invert() {
            return this.source;
        }
    }

    @SuppressWarnings({"unchecked", "rawtypes"}) // This whole class is a mess of generics
    static final class ChainTimeMapper<Ca extends Clock<Ca>, Cb extends Clock<Cb>> implements TimeMapper<Ca, Cb> {
        private final List<TimeMapper<?, ?>> steps;
        private static Clock<?> appendRecursive(List<TimeMapper<?, ?>> dst, Iterable<TimeMapper<?, ?>> src, Clock<?> prev) {
            for (var step : src) {
                Objects.requireNonNull(step, "Step must not be null");
                if (prev != null && !Objects.equals(prev, step.getClockA()))
                    throw new IllegalArgumentException("Steps are not contiguous");
                if (step instanceof ChainTimeMapper) {
                    prev = appendRecursive(dst, ((ChainTimeMapper) step).steps, prev);
                } else {
                    dst.add(step);
                    prev = step.getClockB();
                }
            }
            return prev;
        }
        ChainTimeMapper(List<TimeMapper<?, ?>> steps) {
            Objects.requireNonNull(steps);
            if (steps.isEmpty())
                throw new IllegalArgumentException("No steps");
            this.steps = new ArrayList<>(steps.size());
            appendRecursive(this.steps, steps, null);
        }
        @Override
        public Ca getClockA() {
            var result = (Ca) steps.get(0).getClockA();
            return result;
        }
        @Override
        public Cb getClockB() {
            var result = (Cb) steps.get(steps.size() - 1).getClockB();
            return result;
        }
        @Override
        public Timestamp<Cb> convertAtoB(Timestamp<Ca> timestampA) {
            Timestamp current = timestampA;
            for (var step : this.steps)
                current = step.convertAtoB(current);
            return (Timestamp<Cb>) current;
        }
        @Override
        public Timestamp<Ca> convertBtoA(Timestamp<Cb> timestampB) {
            Timestamp current = timestampB;
            var iter = this.steps.listIterator(this.steps.size());
            while (iter.hasPrevious()) {
                var step = iter.previous();
                current = step.convertBtoA(current);
            }
            return (Timestamp<Ca>) current;
        }
    }
}
