package frc.robot.sensor.vision.moenet;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonProperty.Access;

import edu.wpi.first.math.geometry.Transform3d;

public class MoeNetConfig {
    /**
     * Which direction to send transformations
     */
    public static enum TransformDirection {
        @JsonProperty("sub") RIO_TO_CAM,
        @JsonProperty("pub") CAM_TO_RIO,
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class NetoworkTableConfig implements Cloneable {
        @JsonProperty("log_level") public String logLevel = "ERROR";
        @JsonProperty("subscribeSleep") public boolean subscribeSleep = true;
        // We can't set this property
        @JsonProperty(value="subscribeConfig", access=Access.WRITE_ONLY) public boolean subscribeConfig = true;

        @JsonProperty("publishLog")        public boolean publishLog = true;
        @JsonProperty("publishPing")       public boolean publishPing = true;
        @JsonProperty("publishErrors")     public boolean publishErrors = true;
        @JsonProperty("publishStatus")     public boolean publishStatus = true;
        @JsonProperty("publishConfig")     public boolean publishConfig = true;
        @JsonProperty("publishSystemInfo") public boolean publishSystemInfo = true;
        @JsonProperty("publishDetections") public boolean publishDetections = true;
        @JsonProperty("tfFieldToRobot")    public TransformDirection tfFieldToRobot = TransformDirection.CAM_TO_RIO;
        @JsonProperty("tfFieldToOdom")     public TransformDirection tfFieldToOdom = TransformDirection.CAM_TO_RIO;
        @JsonProperty("tfOdomToRobot")    public TransformDirection tfOdomToRobot = TransformDirection.CAM_TO_RIO;

        public NetoworkTableConfig() {}
        public NetoworkTableConfig(NetoworkTableConfig src) {
            this.logLevel = src.logLevel;
            this.subscribeSleep = src.subscribeSleep;
            this.subscribeConfig = src.subscribeConfig;
            this.publishLog = src.publishLog;
            this.publishPing = src.publishPing;
            this.publishErrors = src.publishErrors;
            this.publishStatus = src.publishStatus;
            this.publishConfig = src.publishConfig;
            this.publishSystemInfo = src.publishSystemInfo;
            this.publishDetections = src.publishDetections;
            this.tfFieldToRobot = Objects.requireNonNull(src.tfFieldToRobot, "tfFieldToRobot");
            this.tfFieldToOdom = Objects.requireNonNull(src.tfFieldToOdom, "tfFieldToOdom");
            this.tfOdomToRobot = Objects.requireNonNull(src.tfOdomToRobot, "tfOdomToRobot");
        }

        @Override
        public NetoworkTableConfig clone() {
            return new NetoworkTableConfig(this);
        }
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    @JsonAutoDetect(getterVisibility = JsonAutoDetect.Visibility.NONE)
    public static class SlamConfig implements Cloneable {
        public final String backend = "sai";
        public boolean syncNN = false;
        public boolean slam = true;
        public boolean vio = false;
        public boolean debugImage = false;
        public int debugImageRate = 0;
        public SlamConfig() {

        }
        public SlamConfig(SlamConfig src) {
            this.syncNN = src.syncNN;
            this.slam = src.slam;
            this.vio = src.vio;
            this.debugImage = src.debugImage;
            this.debugImageRate = src.debugImageRate;
        }

        @Override
        public SlamConfig clone() {
            return new SlamConfig(this);
        }
    }
    @JsonIgnoreProperties(ignoreUnknown = true)
    @JsonAutoDetect(getterVisibility = JsonAutoDetect.Visibility.NONE)
    public static class CameraConfig {
        @JsonProperty public String id;
        @JsonProperty public String selector;
        @JsonProperty public boolean optional = false;
        @JsonProperty public Transform3d robotToCamera;
        @JsonProperty public boolean slam;
        @JsonProperty public Optional<String> objectDetection;
        public CameraConfig(String id, String selector, boolean optional, Transform3d robotToCamera, boolean slam, Optional<String> objectDetection) {
            this.id = Objects.requireNonNull(id);
            this.selector = Objects.requireNonNull(selector);
            this.optional = optional;
            this.robotToCamera = Objects.requireNonNull(robotToCamera);
            this.slam = slam;
            this.objectDetection = Objects.requireNonNull(objectDetection);
        }
        @Override
        public CameraConfig clone() {
            return new CameraConfig(id, selector, optional, robotToCamera, slam, objectDetection);
        }
    }
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class RemoteConfig {
        @JsonProperty("nt") NetoworkTableConfig nt;
        @JsonProperty("slam") SlamConfig slam;
        @JsonProperty("cameras") List<CameraConfig> cameras = null;
        public RemoteConfig() {
        }
        public RemoteConfig(FullConfig source) {
            this.nt = source.nt == null ? null : nt.clone();
            this.slam = source.slam == null ? null : new SlamConfig(slam);
            this.cameras = new ArrayList<>(source.cameras);
        }

        public RemoteConfig addCamera(CameraConfig camera) {
            Objects.requireNonNull(camera);
            if (this.cameras == null)
                this.cameras = new ArrayList<>();
            this.cameras.add(camera);
            return this;
        }
        public RemoteConfig addCamera(String name, String selector, Transform3d robotToCamera, boolean slam, Optional<String> objectDetection) {
            return this.addCamera(new CameraConfig(name, selector, false, robotToCamera, slam, objectDetection));
        }
        public RemoteConfig addSLAMCamera(String name, String selector, Transform3d robotToCamera) {
            return addCamera(name, selector, robotToCamera, true, Optional.empty());
        }
        public RemoteConfig addObjectDetectionCamera(String name, String selector, Transform3d robotToCamera, String objectDetection) {
            return addCamera(name, selector, robotToCamera, false, Optional.of(objectDetection));
        }
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    @JsonAutoDetect(getterVisibility = JsonAutoDetect.Visibility.NONE)
    public static class FullConfig {
        @JsonProperty public NetoworkTableConfig nt;
        @JsonProperty public SlamConfig slam;
        @JsonProperty public List<CameraConfig> cameras;
    }
}
