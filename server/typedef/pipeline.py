"Pipeline stage configuration"

from typing import TYPE_CHECKING, Literal, Optional, Union, Annotated, ClassVar, Self
import typing
from pydantic import BaseModel, Field, Tag, Discriminator, RootModel
from pathlib import Path
from enum import StrEnum
from abc import ABC
import depthai as dai

if __package__ is None:
	import apriltag, util
else:
	from . import apriltag, util

# Helper for DAI types
if TYPE_CHECKING:
	RgbSensorResolution = dai.ColorCameraProperties.SensorResolution
	MonoSensorResolution = dai.MonoCameraProperties.SensorResolution
	CameraBoardSocket = dai.CameraBoardSocket
else:
	RgbSensorResolution = util.wrap_dai_enum(dai.ColorCameraProperties.SensorResolution)
	MonoSensorResolution = util.wrap_dai_enum(dai.MonoCameraProperties.SensorResolution)
	CameraBoardSocket = util.wrap_dai_enum(dai.CameraBoardSocket)

class NNConfig(BaseModel):
	"Base config for NN"
	confidence_threshold: float
	iou_threshold: float
	labels: list[str]
	depthLowerThreshold: int
	depthUpperThreshold: int
	classes: int
	coordinateSize: int
	anchors: list[float]
	anchor_masks: dict[str, list[int]]

class BaseStageConfig[S: str](BaseModel, ABC):
	infer: ClassVar[bool] = False
	"Can we infer this stage?"
	merge: ClassVar[bool] = False
	"Should we merge stages with the same name?"

	@classmethod
	def factory(cls, *, merge: bool = False, implicit: bool = False) -> type[Self]:
		"Make customized BaseStageConfig inheritance (fix 'stage' field)"
		_merge = merge
		S_val: type[S] = cls.__pydantic_generic_metadata__['args'][0]
		assert typing.get_origin(S_val) == Literal
		name: S = typing.get_args(S_val)[0]

		class _ModelHelper(cls, ABC):
			merge: ClassVar[bool] = _merge
			infer: ClassVar[bool] = implicit
			# Use default_factory to exclude default JSON
			stage: S_val = (# type: ignore
				Field(description="Stage name", default_factory=lambda: name) 
			)
		return typing.cast(type[Self], _ModelHelper)
	
	stage: S = Field(description="Stage name", default_factory=lambda: NotImplementedError())
	enabled: bool = Field(default=True, description="Is this stage enabled?")
	optional: bool = Field(default=False, description="If there's an error constructing this stage, is that a pipeline failure?")

	@property
	def name(self):
		if (target := getattr(self, 'target', None)) is not None:
			return f'{self.stage}.{target}'
		return self.stage

class InheritStageConfig(BaseStageConfig[Literal['inherit']].factory()):
	"Include another defined pipeline"
	id: str

class ColorCameraStageConfig(BaseStageConfig[Literal['rgb']].factory(merge=True, implicit=True)):
	"Configure the RGB camera"
	resolution: RgbSensorResolution | None = Field(default=None, description="Camera sensor resolution")
	fps: float | None = Field(default=None, description='Max FPS')


class MonoCameraStageConfig(BaseStageConfig[Literal['mono']].factory(implicit=True)):
	"Configure mono camera"
	target: Literal["left", "right"]
	resolution: MonoSensorResolution | None = Field(default=None, description='Camera sensor resolution')
	fps: float | None = Field(default=None, description='Max FPS')
	

class StereoDepthStageConfig(BaseStageConfig[Literal['depth']].factory()):
	"Configure stereo depth"
	checkLeftRight: bool | None = Field(default=None, description="Enable Left-Right check")
	extendedDisparity: bool | None = Field(default=None, description="Enable extended disparity mode")
	preset: Literal[
		'high_accuracy',
		'high_density',
		None,
	] = Field(default=None, description='Set preset profile')


class ObjectDetectionStageConfig(BaseStageConfig[Literal['nn']].factory()):
	config: Union[NNConfig, Path]
	blobPath: Path

class VideoDisplayTarget(StrEnum):
	"Name of video stream for user consumption"
	LEFT = 'left'
	"Left monocular camera"
	RIGHT = 'right'
	"Right monocular camera"
	RGB = 'rgb'
	"Color camera"
	DEPTH = 'depth'

class WebStreamStageConfig(BaseStageConfig[Literal['web']].factory()):
	"Stream data to web"
	target: VideoDisplayTarget
	maxFramerate: Optional[int] = Field(None, gt=0, description="Maximum framerate for stream")
	@property
	def name(self):
		return f'{self.stage}.{self.target}'

class SaveStageConfig(BaseStageConfig[Literal['save']].factory()):
	"Save images to file"
	target: VideoDisplayTarget
	path: Path
	maxFramerate: Optional[float] = Field(default=None, gt=0, description="Maximum framerate for stream")

class ShowStageConfig(BaseStageConfig[Literal['show']].factory()):
	"Show video stream as GUI"
	target: VideoDisplayTarget

class AprilTagStageConfigBase(BaseStageConfig[Literal['apriltag']].factory()):
	runtime: Literal["device", "host"] = Field("host")
	camera: Literal["left", "right", "rgb"] = Field("left")

	# AprilTag detector runtime
	detectorThreads: int | None = Field(default=None, ge=0, title="Detector Threads", description="How many threads should be used for computation")
	detectorAsync: bool = Field(False, title="Detector Async", description="Should we run the detector on a different thread? Only useful if we're doing multiple things with the same camera")

	# AprilTag detector params
	decodeSharpening: float | None = Field(default=None, ge=0, title="Decode Sharpening", description="How much sharpening should be done to decoded images")
	quadDecimate: int = Field(1)
	quadSigma: float = Field(0.0)
	refineEdges: bool = Field(True, title="Refine Edges")
	# Filter
	hammingDist: int = Field(default=0, ge=0, lt=3, title="Hamming Distance", description="Maximum number of bits to correct")
	decisionMargin: int = Field(35, ge=0, title="Decision Margin")

	# Pose
	numIterations: int = Field(40)
	undistort: bool = Field(False, description="Should we try to undistort the camera lens?")
	solvePNP: bool = Field(True, title="Solve PnP")
	doMultiTarget: bool = Field(False, title="Do Multi-Target")
	doSingleTargetAlways: bool = Field(False, title="Do Single Target Always")

class AprilTagStageConfig(AprilTagStageConfigBase):
	apriltags: apriltag.AprilTagField

class WorkerAprilTagStageConfig(AprilTagStageConfigBase):
	apriltags: apriltag.AprilTagFieldInlineWpi


class SlamStageConfig(BaseStageConfig[Literal['slam']].factory()):
	"SAI slam"
	slam: bool = Field(default=True)
	vio: bool = Field(default=False, description="Enable VIO")
	map_save: Optional[Path] = Field(default=None)
	map_load: Optional[Path] = Field(default=None)
	waitForPose: bool = Field(False, description="Wait for external pose before emitting data")
	apriltags: Union[apriltag.AprilTagFieldRef, apriltag.AprilTagFieldInline, None] = Field(None)

class WorkerSlamStageConfig(SlamStageConfig):
	"Resolved version of 'SlamStageConfig"
	apriltags: Optional[apriltag.AprilTagFieldRefSai]

class TelemetryStageConfig(BaseStageConfig[Literal['telemetry']].factory()):
	pass

class ImuStageConfig(BaseStageConfig[Literal['imu']].factory()):
	pass

PipelineStage = Annotated[
	Union[
		Annotated[InheritStageConfig, Tag("inherit")],
		Annotated[ColorCameraStageConfig, Tag("rgb")],
		Annotated[MonoCameraStageConfig, Tag("mono")],
		Annotated[StereoDepthStageConfig, Tag("depth")],
		Annotated[ObjectDetectionStageConfig, Tag("nn")],
		Annotated[AprilTagStageConfig, Tag("apriltag")],
		Annotated[SlamStageConfig, Tag("slam")],
		Annotated[WebStreamStageConfig, Tag("web")],
		Annotated[SaveStageConfig, Tag("save")],
		Annotated[ShowStageConfig, Tag("show")],
		Annotated[ImuStageConfig, Tag("imu")],
		Annotated[TelemetryStageConfig, Tag("telemetry")],
	],
	Discriminator("stage")
]

PipelineStageWorker = Annotated[
	Union[
		# Annotated[InheritStage, Tag("inherit")],
		Annotated[ColorCameraStageConfig, Tag("rgb")],
		Annotated[MonoCameraStageConfig, Tag("mono")],
		Annotated[StereoDepthStageConfig, Tag("depth")],
		Annotated[ObjectDetectionStageConfig, Tag("nn")],
		Annotated[WorkerAprilTagStageConfig, Tag("apriltag")],
		Annotated[WorkerSlamStageConfig, Tag("slam")],
		Annotated[WebStreamStageConfig, Tag("web")],
		Annotated[SaveStageConfig, Tag("save")],
		Annotated[ShowStageConfig, Tag("show")],
		Annotated[ImuStageConfig, Tag("imu")],
		Annotated[TelemetryStageConfig, Tag("telemetry")],
	],
	Discriminator("stage")
]

class PipelineConfig(RootModel[list[PipelineStage]]):
	pass
class PipelineConfigWorker(RootModel[list[PipelineStageWorker]]):
	pass