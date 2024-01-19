package frc.robot.sensor.vision.io;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import edu.wpi.first.util.protobuf.Protobuf;
import edu.wpi.first.util.protobuf.ProtobufSerializable;
import us.hebi.quickbuf.Descriptors.Descriptor;

public class ObjectDetections implements ProtobufSerializable {
    public static final ObjectDetectionsProto proto = new ObjectDetectionsProto();

    private final List<? extends ObjectDetection> detections;

    public ObjectDetections(List<? extends ObjectDetection> detections) {
        this.detections = new ArrayList<>(detections);
    }

    public List<? extends ObjectDetection> getDetections() {
        return detections;
    }

    static class ObjectDetectionsProto implements Protobuf<ObjectDetections, com.mindlin.moenet.proto.ObjectDetections> {
        @Override
        public Class<ObjectDetections> getTypeClass() {
            return ObjectDetections.class;
        }

        @Override
        public Descriptor getDescriptor() {
            return com.mindlin.moenet.proto.ObjectDetections.getDescriptor();
        }

        @Override
        public com.mindlin.moenet.proto.ObjectDetections createMessage() {
            return com.mindlin.moenet.proto.ObjectDetections.newInstance();
        }

        @Override
        public ObjectDetections unpack(com.mindlin.moenet.proto.ObjectDetections msg) {
            List<String> labels;
            {
                var rawLabels = msg.getLabels();
                labels = new ArrayList<>(rawLabels.capacity());
                rawLabels.forEach(labels::add);
            }
            
            var rawDetections = msg.getDetections();
            var detections = new ArrayList<ObjectDetection>(rawDetections.length());
            for (var rawDetection : rawDetections) {
                detections.add(ObjectDetection.unpack(labels, rawDetection));
            }

            return new ObjectDetections(detections);
        }

        @Override
        public void pack(com.mindlin.moenet.proto.ObjectDetections msg, ObjectDetections value) {
            Map<String, Integer> labelLUT = new HashMap<>();

            for (var detection : value.detections) {
                var labelId = labelLUT.get(detection.getLabel());
                if (labelId == null) {
                    labelId = labelLUT.size();
                    msg.addLabels(detection.getLabel());
                    labelLUT.put(detection.getLabel(), labelId);
                }

                var msgDetection = com.mindlin.moenet.proto.ObjectDetection.newInstance()
                    .setLabelId(labelId)
                    .setConfidence(detection.getConfidence())
                    .setTimestamp(InstantProto.proto.pack(detection.getTimestamp()));
                
                if (detection.getPoseField() != null) {
                    msgDetection.setPositionField(Translation3dProto.INSTANCE.pack(detection.getPoseField()));
                }
                if (detection.getPoseRobot() != null) {
                    msgDetection.setPositionRobot(Translation3dProto.INSTANCE.pack(detection.getPoseRobot()));
                }
                msg.addDetections(msgDetection);
            }
        }

    }
}
