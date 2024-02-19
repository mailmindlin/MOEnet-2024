"Type definitions for parsing the configuration"

from typing import TYPE_CHECKING, Optional, Literal, Union, Annotated
import enum
from pathlib import Path
from datetime import timedelta

from pydantic import BaseModel, Field, TypeAdapter, Tag, ByteSize
from ntcore import NetworkTableInstance

if __name__ == '__main__' and (not TYPE_CHECKING):
	import common, geom, apriltag, pipeline
else:
	from . import common, geom, apriltag, pipeline

class ObjectTrackerConfig(BaseModel):
	"Configuration for tracking object detections over time"
	min_detections: int = Field(8, gt=0, description="Number of times to have seen an object before accepting it")
	detected_duration: timedelta = Field(timedelta(seconds=1), description="Length of time to keep an object detecting (seconds)")
	history_duration: timedelta = Field(timedelta(seconds=8), description="Length of time to retain an object detection (seconds)")
	clustering_distance: float = Field(0.3, gt=0, description="")
	min_depth: float = Field(0.5, gt=0, description="")
	alpha: float = Field(0.2, gt=0, description="")

class AprilTagStrategy(enum.StrEnum):
	LOWEST_AMBIGUITY = enum.auto()
	CLOSEST_TO_LAST_POSE = enum.auto()
	AVERAGE_BEST_TARGETS = enum.auto()

class PoseEstimatorConfig(BaseModel):
	history: timedelta = Field(timedelta(seconds=3), description="Length of pose replay buffer (seconds)")
	force2d: bool = Field(True, description="Should we force the pose to fit on the field?")
	apriltagStrategy: AprilTagStrategy | None = Field(default=AprilTagStrategy.LOWEST_AMBIGUITY)
	odometryStdDevs: list[float] = Field()

class PoseEstimatorConfig1(BaseModel):
	publish_transform: bool = Field(True)
	publish_acceleration: bool = Field(False)
	permit_corrected_publication: bool = Field(False)
	reset_on_time_jump: bool = Field(False)
	use_control: bool = Field(False)

	apriltagStrategy: AprilTagStrategy | None = Field(default=AprilTagStrategy.LOWEST_AMBIGUITY)

	smooth_lagged_data: bool = Field(False)
	history_length: timedelta = Field(timedelta(seconds=0.0))
	force_2d: bool = Field(False)
	update_frequency: float = Field(30)
	publish_transform = Field(True)
	print_diagnostics: bool = Field(False)
	predict_to_current_time: bool = Field(False)
	"""
	By default, the filter predicts and corrects up to the time of the
	latest measurement. If this is set to true, the filter does the same, but
	then also predicts up to the current time step.
	"""
	acceleration_limits: tuple[float, float, float, float, float, float] | None = Field(None)
	acceleration_gains: tuple[float, float, float, float, float, float] | None = Field(None)
	deceleration_limits: tuple[float, float, float, float, float, float] | None = Field(None)
	deceleration_gains: tuple[float, float, float, float, float, float] | None = Field(None)

class EstimatorConfig(BaseModel):
	detections: ObjectTrackerConfig = Field(default_factory=ObjectTrackerConfig)
	pose: PoseEstimatorConfig = Field(default_factory=PoseEstimatorConfig)


class WebConfig(BaseModel):
	"Configure webserver"
	enabled: bool = Field(True)
	host: Optional[str] = Field(None, description="Host for HTTP server")
	port: Optional[int] = Field(8080, gt=0, description="Port for HTTP server")
	video_codec: Optional[str] = Field(None, description="Force a specific video codec (e.g. video/H264)")
	cert_file: Optional[Path] = Field(None, description="SSL certificate file (for HTTPS)")
	key_file: Optional[Path] = Field(None, description="SSL key file (for HTTPS)")

class NetworkTablesDirection(enum.Enum):
	"Which direction to send data?"
	SUBSCRIBE = 'sub'
	"Subscribe to topic"
	PUBLISH = 'pub'
	"Publish topic"
	DISABLED = False
	"Do not publish or subscribe"

class NetworkTablesConfig(BaseModel):
	"Configure NetworkTables. Must be provided locally"
	enabled: bool = Field(True, description="Should anything be sent to NetworkTables?")

	# Connection info
	team: int = Field(365, description="FRC team number")
	port: int = Field(NetworkTableInstance.kDefaultPort4, description="Which port should we connect to?")
	host: Optional[str] = Field(None, description="NetworkTables host IP")
	client_id: str = Field("MOEnet", description="Client connection name")
	
	table: str = Field("moenet", description="Root table name")

	log_level: str = Field("error", description="Minimum level to send logs")
	log_lines: int = Field(10, description="Number of log lines to retain")

	# Subscriptions
	subscribeSleep: bool = Field(True, description="Should we listen for sleep control at `/moenet/rio_request_sleep`?")
	subscribeConfig: bool = Field(True, description="Should we listen for config updates at `/moenet/rio_dynamic_config`?")

	# Utility publications
	publishLog: bool = Field(True, description="Should we publish logs to `/moenet/client_log`?")
	publishPing: bool = Field(True, description="Should we publish ping updates to `/moenet/client_ping`?")
	publishErrors: bool = Field(True, description="Should we publish errors updates to `/moenet/client_error`?")
	publishStatus: bool = Field(True)
	publishConfig: bool = Field(True, description="Should we publish this config to `/moenet/client_config`?")
	publishSystemInfo: bool = Field(True, description="Should we publish system info to `/moenet/client_telemetry`?")
	publishDetections: bool = Field(True, description="Publish object detections to `/moenet/client_detections`")

	# Transforms
	tfFieldToRobot: NetworkTablesDirection = Field(default=NetworkTablesDirection.PUBLISH, description="field -> robot transform (absolute pose)")
	tfFieldToOdom: NetworkTablesDirection = Field(default=NetworkTablesDirection.PUBLISH, description="field -> odom transform (odometry estimate)")
	tfOodomToRobot: NetworkTablesDirection = Field(default=NetworkTablesDirection.PUBLISH, description="odom->robot transform (odometry correction)")
	subscribePoseOverride: bool = Field(True, description="Allow the Rio to override poses")
	publishField2dF2O: bool = Field(False, description="Publish Field2d widget (field->odom)")
	publishField2dF2R: bool = Field(False, description="Publish Field2d widget (field->robot)")
	publishField2dDets: bool = Field(False, description="Publish Field2d widget (field->notes)")


class ObjectDetectionDefinitionBase(BaseModel):
	"Configure an object detection pipeline"
	id: str
	blobPath: Path = Field(description="Path to NN blob")

class ObjectDetectionDefinitionRef(ObjectDetectionDefinitionBase):
	configPath: Optional[Path] = Field(description="Path to NN config")
	"Configuration path (relative to config file)"

class ObjectDetectionDefinitionInline(ObjectDetectionDefinitionBase):
	config: Optional[pipeline.NNConfig] = Field(description="Inline NN config")

ObjectDetectionDefinition = TypeAdapter(Union[
	Annotated[ObjectDetectionDefinitionInline, Tag("inline")],
	Annotated[ObjectDetectionDefinitionRef, Tag("reference")],
])


class NavXConfig(BaseModel):
	"NavX configuration"
	port: Literal["usb", "usb1", "usb2"] = Field("usb", description="NavX connection")
	update_rate: int = Field(60, description="NavX poll rate (in hertz)", gt=0, le=255)

PipelineConfig = pipeline.PipelineConfig

class PipelineDefinition(BaseModel):
	id: str
	stages: PipelineConfig


class CameraConfig(BaseModel):
	name: Optional[str] = Field(None, description="Human-readable name")
	selector: Union[str, common.OakSelector] = Field(description="Which camera are we referencing?")
	max_usb: Optional[Literal["FULL", "HIGH", "LOW", "SUPER", "SUPER_PLUS", "UNKNOWN"]] = Field(None)
	retry: common.RetryConfig = Field(default_factory=common.RetryConfig)
	pose: Optional[geom.Transform3d] = Field(description="Camera pose (in robot-space)")
	dynamic_pose: Optional[str] = Field(None, description="If this camera can move, this is it's network name")
	pipeline: Union[PipelineConfig, str, None] = Field(None, description="Configure pipeline")

class LogConfig(BaseModel):
	"""
	Configuration for logging output
	"""
	level: Literal['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL'] = Field('DEBUG')
	file: Optional[Path] = Field(None)


class DataLogConfig(BaseModel):
	"Configuration for datalog"
	enabled: bool = Field(True)
	folder: Optional[Path] = Field(None)
	mkdir: bool = Field(False, description="Make log folder if it doesn't exist?")
	cleanup: bool = Field(False, description="Should we clean up old log files? (see free_space and max_logs)")
	free_space: Optional[int] = Field(None, description="Minimum free size before we don't make more logs/clean up old ones")
	max_logs: Optional[int] = Field(None, description="Maximum number of log files to retain (requires cleanup)")


class CameraSelectorDefinition(common.OakSelector):
	"Define a camera selector"
	id: str = Field(description="ID to reference this definition by")
	name: Optional[str] = Field(None)
	pose: Optional[geom.Transform3d] = Field(None, description="Robot-to-camera transform")
	dynamic_pose: Optional[str] = Field(None, description="If this camera can move, this is it's network name")


class LocalConfig(BaseModel):
	"Local config data"
	allow_overwrite: bool = Field(False, description="Allow remote changes to overwrite this config?")
	nt: NetworkTablesConfig = Field(default_factory=lambda: NetworkTablesConfig(enabled=False), title="NetworkTables", description="NetworkTables data")
	timer: Union[Literal["system"], NavXConfig] = Field("system", description="Timer for synchronizing with RoboRIO")
	log: LogConfig = Field(default_factory=DataLogConfig)
	datalog: DataLogConfig = Field(default_factory=lambda: DataLogConfig(enabled=False))
	estimator: EstimatorConfig = Field(default_factory=EstimatorConfig)
	camera_selectors: list[CameraSelectorDefinition] = Field(default_factory=list)
	cameras: list[CameraConfig] = Field(None, description="Configuration for individual cameras")
	pipelines: list[PipelineDefinition] = Field(default_factory=list, description="Reusable pipelines")
	web: WebConfig = Field(default_factory=lambda: WebConfig(enabled=False))

	def merge(self, update: 'RemoteConfig') -> 'LocalConfig':
		"Merge in a remote configuration"
		result = self.model_copy()
		if update.slam is not None:
			result.slam = update.slam
		# if update.cameras is not None:
		#     for i, camera in enumerate(update.cameras):
		#         if isinstance(camera.slam, SlamConfig) and isinstance(camera.slam.apriltag, (AprilTagFieldFRCRef, AprilTagFieldSAIRef)):
		#             raise ValueError(f'Invalid remote config: camera #{i} has a file reference')
		#     result.cameras = update.cameras


class RemoteConfig(BaseModel):
	cameras: list[CameraConfig]


if __name__ == '__main__':
	import argparse, sys, typing
	parser = argparse.ArgumentParser(description='Dump schema to file')

	types = {
		'LocalConfig': LocalConfig,
		'RemoteConfig': RemoteConfig,
	}
	parser.add_argument('type', choices=types.keys(), help='Type to dump', default='LocalConfig')
	parser.add_argument('--format', choices=['json', 'proto'], default='json')
	parser.add_argument('-o', '--out', type=str, default='-')

	args = parser.parse_args()

	def dump(stream: typing.TextIO):
		dump_type: BaseModel = types[args.type]
		match args.format:
			case 'json':
				import json
				json.dump(dump_type.model_json_schema(), stream, indent='\t')
			case 'proto':
				dump_type.model_dump()
				raise NotImplementedError()#TODO
	
	if args.out == '-':
		dump(sys.stdout)
	else:
		with open(args.out, 'w') as f:
			dump(f)
