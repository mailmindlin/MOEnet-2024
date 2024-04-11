package frc.robot.sensor.vision;

public interface VisionSystem extends AutoCloseable {
    public static enum Status {
        /**
         * The camera system hasn't started yet
         */
        NOT_READY,
        /**
         * The camera system is initializing
         */
        INITIALIZING,
        /**
         * The camera system is working, and able to send/sending data
         */
        READY,
        /**
         * The camera system is temporarily disabled, in some low-power mode
         */
        SLEEPING,
        /**
         * The camera system encountered an error (that may be recoverable)
         */
        ERROR,
        /**
         * The camera system encountered an unrecoverable error
         */
        FATAL,
    }

    /** Get current status */
    Status getStatus();

    boolean isConnected();
    boolean canSleep();
    void setSleeping(boolean sleeping);

    default void periodic() {}
}
