package frc.robot.sensor.vision.moenet;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import edu.wpi.first.math.geometry.Pose3d;
import edu.wpi.first.math.geometry.Transform3d;
import edu.wpi.first.networktables.BooleanPublisher;
import edu.wpi.first.networktables.IntegerSubscriber;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.networktables.ProtobufSubscriber;
import edu.wpi.first.networktables.PubSubOption;
import edu.wpi.first.networktables.StringPublisher;
import edu.wpi.first.networktables.StringSubscriber;
import edu.wpi.first.networktables.StructEntry;
import edu.wpi.first.util.datalog.DataLog;
import edu.wpi.first.util.datalog.StructLogEntry;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.Timer;
import frc.robot.sensor.time.TimeUtil;
import frc.robot.sensor.time.Timestamped;
import frc.robot.sensor.vision.VisionSystem.State;
import frc.robot.sensor.vision.io.InstantProto;
import frc.robot.sensor.vision.io.InstantStruct;
import frc.robot.sensor.vision.io.Mat66Struct;
import frc.robot.sensor.vision.io.ObjectDetection;
import frc.robot.sensor.vision.io.ObjectDetections;
import frc.robot.sensor.vision.io.PositionEstimate;
import frc.robot.sensor.vision.io.Translation3dProto;
import frc.robot.sensor.vision.moenet.MoeNetConfig.TransformDirection;

public class MoeNet implements AutoCloseable {
	public static final long TIMEOUT_US = 5_000_000; // 5 seconds
	public static final String DEFAULT_NAME = "moenet";
	
	private State state = State.NOT_READY;

	private final NetworkTableInstance nt;
	private final String name;
	private final IntegerSubscriber subPing;
	private final IntegerSubscriber subStatus;
	private final StringSubscriber subConfig;
	private final StructEntry<Pose3d> tfFieldOdom;
	private final StructEntry<PositionEstimate> tfFieldRobot;
	private final StructEntry<Transform3d> tfOdomRobot;
	private final ProtobufSubscriber<ObjectDetections> subObjectDetections;
	private final StringPublisher pubConfig;
	private final BooleanPublisher pubSleep;

	private final DataLog log;
	private final StructLogEntry<Pose3d> logTfFieldOdom;
	private final StructLogEntry<PositionEstimate> logTfFieldRobot;
	private final StructLogEntry<Transform3d> logTfOdomRobot;

	private final ObjectMapper json = new ObjectMapper();

	private long lastConfigTimestamp = 0;
	private MoeNetConfig.FullConfig lastConfig = null;
	private long lastOdomToRobotTs = 0;
	private long lastFieldToRobotTs = 0;
	private long lastFieldToOdomTs = 0;

	private List<ObjectDetection> detections = new ArrayList<>();
	
	public MoeNet(NetworkTableInstance nt, DataLog log, String name) {
		this.nt = Objects.requireNonNull(nt, "nt");
		this.name = Objects.requireNonNull(name, "name");

		var table = nt.getTable(name);
		nt.addSchema(Pose3d.struct);
		nt.addSchema(Transform3d.struct);
		nt.addSchema(InstantProto.proto);
		nt.addSchema(InstantStruct.struct);
		nt.addSchema(Mat66Struct.struct);
		nt.addSchema(ObjectDetections.proto);
		nt.addSchema(PositionEstimate.struct);
		nt.addSchema(Translation3dProto.INSTANCE);

		this.subPing = table.getIntegerTopic("client_ping").subscribe(0);
		this.subStatus = table.getIntegerTopic("client_status").subscribe(0);
		this.subConfig = table.getStringTopic("client_config").subscribe("");
		this.pubConfig = table.getStringTopic("rio_config").publish(PubSubOption.sendAll(true));
		this.pubSleep = table.getBooleanTopic("rio_sleep").publish(PubSubOption.sendAll(true));
		this.tfFieldOdom = table.getStructTopic("tf_field_odom", Pose3d.struct).getEntry(null, PubSubOption.excludeSelf(true));
		this.tfFieldRobot = table.getStructTopic("tf_field_robot", PositionEstimate.struct).getEntry(null, PubSubOption.excludeSelf(true));
		this.tfOdomRobot = table.getStructTopic("tf_odom_robot", Transform3d.struct).getEntry(null, PubSubOption.excludeSelf(true));
		this.subObjectDetections = table.getProtobufTopic("client_detections", ObjectDetections.proto).subscribe(null);

		this.log = log;
		if (this.log != null) {
			log.addSchema(Pose3d.struct);
			log.addSchema(Transform3d.struct);
			this.logTfFieldOdom = StructLogEntry.create(log, "moenet/tf_field_odom", Pose3d.struct);
			this.logTfFieldRobot = StructLogEntry.create(log, "moenet/tf_field_robot", PositionEstimate.struct);
			this.logTfOdomRobot = StructLogEntry.create(log, "moenet/tf_odom_robot", Transform3d.struct);
		} else {
			this.logTfFieldOdom = null;
			this.logTfFieldRobot = null;
			this.logTfOdomRobot = null;
		}
	}

	public Optional<MoeNetConfig.FullConfig> getConfig() {
		var configValue = this.subConfig.getAtomic();
		// No config to read
		if (configValue.timestamp == 0 || configValue.value == null || Objects.equals(configValue.value, ""))
			return Optional.empty();
		
		// Use cache if it hasn't changed
		if (configValue.timestamp <= this.lastConfigTimestamp)
			return Optional.of(this.lastConfig);
		
		try {
			var result = json.readValue(configValue.value, MoeNetConfig.FullConfig.class);
			this.lastConfig = result;
			this.lastConfigTimestamp = configValue.timestamp;

			return Optional.of(result);
		} catch (JsonProcessingException e) {
			DriverStation.reportError("Error decoding MOEnet config", true);
			return Optional.empty();
		}
	}

	public void setConfig(MoeNetConfig.RemoteConfig config) {
		String configString;
		try {
			configString = json.writeValueAsString(config);
		} catch (JsonProcessingException e) {
			DriverStation.reportError("Error serializing MOEnet config: " + e.getMessage(), true);
			return;
		}
		this.pubConfig.set(configString);
	}

	public State getState() {
		long stateId = this.subStatus.get(0);
		switch ((int) stateId) {
			case 0:
				return State.NOT_READY;
			case 1:
				return State.INITIALIZING;
			case 2:
				return State.READY;
			case 3:
				return State.SLEEPING;
			case 4:
				return State.ERROR;
			case 5:
				return State.FATAL;
			default:
				DriverStation.reportWarning("Unknown MOEnet state: " + stateId, false);
				return State.ERROR;
		}
	}

	public boolean isConnected() {
		var lastPing = this.subPing.getAtomic(0);
		if (lastPing.timestamp == 0)
			return false;
		// NT timestamp is in microseconds
		var now = (long) (Timer.getFPGATimestamp() * 1_000_000);
		return (now - lastPing.timestamp) < TIMEOUT_US;
	}

	public boolean canSleep() {
		return true;
	}

	public void setSleeping(boolean sleeping) {
		this.pubSleep.set(sleeping);
	}

	public void sendFieldToOdom(Pose3d fieldToOdom) {
		var config = this.getConfig();
		if (config.isEmpty())
			return;
		if (config.get().nt.tfFieldToOdom == TransformDirection.RIO_TO_CAM) {
			this.tfFieldOdom.set(fieldToOdom);
		}
	}

	public void sendFieldToRobot(PositionEstimate fieldToRobot) {
		var config = this.getConfig();
		if (config.isEmpty())
			return;
		if (config.get().nt.tfFieldToRobot == TransformDirection.RIO_TO_CAM) {
			this.tfFieldRobot.set(fieldToRobot);
		}
	}

	public void sendOdomToRobot(Transform3d odomToRobot) {
		var config = this.getConfig();
		if (config.isEmpty())
			return;
		if (config.get().nt.tfOodomToRobot == TransformDirection.RIO_TO_CAM) {
			this.tfOdomRobot.set(odomToRobot);
		}
	}

	public Optional<Timestamped<Pose3d>> getFieldToOdom() {
		var config = this.getConfig();
		if (config.isEmpty() || config.get().nt.tfFieldToOdom == TransformDirection.CAM_TO_RIO) {
			var entry = this.tfFieldOdom.getAtomic();
			if (entry.timestamp > this.lastFieldToOdomTs) {
				this.lastFieldToOdomTs = entry.timestamp;
				this.logTfFieldOdom.append(entry.value, entry.timestamp);
				return Optional.of(new Timestamped<>(TimeUtil.fromMicros(entry.timestamp), entry.value));
			}
		}
		return Optional.empty();
	}

	public Optional<PositionEstimate> getFieldToRobot() {
		var config = this.getConfig();
		// Check that we're supposed to be reading this
		if (config.isEmpty() || config.get().nt.tfFieldToRobot == TransformDirection.CAM_TO_RIO) {
			var entry = this.tfFieldRobot.getAtomic();
			if (entry.timestamp > this.lastFieldToRobotTs) {
				this.lastFieldToRobotTs = entry.timestamp;
				this.logTfFieldRobot.append(entry.value, entry.timestamp);
				return Optional.of(entry.value);
			}
		}
		return Optional.empty();
	}

	public Optional<Timestamped<Transform3d>> getOdomToRobot() {
		var config = this.getConfig();
		if (config.isEmpty() || config.get().nt.tfOodomToRobot == TransformDirection.CAM_TO_RIO) {
			var entry = this.tfOdomRobot.getAtomic();
			if (entry.timestamp > this.lastOdomToRobotTs) {
				this.lastOdomToRobotTs = entry.timestamp;
				this.logTfOdomRobot.append(entry.value, entry.timestamp);
				return Optional.of(new Timestamped<>(TimeUtil.fromMicros(entry.timestamp), entry.value));
			}
		}
		return Optional.empty();
	}

	public List<ObjectDetection> getDetections() {
		return this.detections;
	}

	public void periodic() {
		try {
			this.getConfig();
		} catch (Exception e) {
			DriverStation.reportError("Error refreshing config", true);
		}
	}

	@Override
	public void close() throws Exception {
		this.subPing.close();
		this.subStatus.close();
		this.subConfig.close();
		this.tfFieldOdom.close();
		this.tfFieldRobot.close();
		this.tfOdomRobot.close();
		this.subObjectDetections.close();

		throw new UnsupportedOperationException("Unimplemented method 'close'");
	}
}
