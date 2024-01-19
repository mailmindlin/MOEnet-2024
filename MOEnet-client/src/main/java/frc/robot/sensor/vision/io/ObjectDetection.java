package frc.robot.sensor.vision.io;

import java.time.Instant;
import java.util.List;

import edu.wpi.first.math.geometry.Translation3d;

public class ObjectDetection {
    static ObjectDetection unpack(List<String> labels, com.mindlin.moenet.proto.ObjectDetection msg) {
        var label = labels.get(msg.getLabelId());
        var confidence = msg.getConfidence();
        var timestampRaw = msg.getTimestamp();
        var timestamp = Instant.ofEpochSecond(timestampRaw.getSeconds(), timestampRaw.getNanos());
        var poseField = Translation3dProto.INSTANCE.unpack(msg.getPositionField());
        var poseRobot = Translation3dProto.INSTANCE.unpack(msg.getPositionRobot());
        return new ObjectDetection(label, confidence, timestamp, poseField, poseRobot);
    }

    private final String label;
    private final double confidence;
    private final Instant timestamp;

    private final Translation3d poseField;
    private final Translation3d poseRobot;

    public ObjectDetection(String label, double confidence, Instant timestamp, Translation3d poseField, Translation3d poseRobot) {
        this.label = label;
        this.confidence = confidence;
        this.timestamp = timestamp;
        this.poseField = poseField;
        this.poseRobot = poseRobot;
    }

    public String getLabel() {
        return label;
    }

    public double getConfidence() {
        return confidence;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public Translation3d getPoseField() {
        return poseField;
    }

    public Translation3d getPoseRobot() {
        return poseRobot;
    }

    @Override
    public String toString() {
        return "ObjectDetection [label=" + label + ", confidence=" + confidence + ", poseField=" + poseField
                + ", poseRobot=" + poseRobot + "]";
    }

    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((label == null) ? 0 : label.hashCode());
        long temp;
        temp = Double.doubleToLongBits(confidence);
        result = prime * result + (int) (temp ^ (temp >>> 32));
        result = prime * result + ((poseField == null) ? 0 : poseField.hashCode());
        result = prime * result + ((poseRobot == null) ? 0 : poseRobot.hashCode());
        return result;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj)
            return true;
        if (obj == null)
            return false;
        if (getClass() != obj.getClass())
            return false;
        ObjectDetection other = (ObjectDetection) obj;
        if (label == null) {
            if (other.label != null)
                return false;
        } else if (!label.equals(other.label))
            return false;
        if (Double.doubleToLongBits(confidence) != Double.doubleToLongBits(other.confidence))
            return false;
        if (poseField == null) {
            if (other.poseField != null)
                return false;
        } else if (!poseField.equals(other.poseField))
            return false;
        if (poseRobot == null) {
            if (other.poseRobot != null)
                return false;
        } else if (!poseRobot.equals(other.poseRobot))
            return false;
        return true;
    }
}
