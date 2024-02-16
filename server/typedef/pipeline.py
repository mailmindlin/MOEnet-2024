"Pipeline stage configuration"

from typing import TYPE_CHECKING, Literal, Optional, Union, Annotated, TypeVar, Generic, ClassVar, TypeAlias
from pydantic import BaseModel, Field, Tag, Discriminator, RootModel, create_model
from pathlib import Path
from enum import StrEnum
from abc import ABC
import depthai as dai

try:
	from . import apriltag, util
except ImportError:
	import apriltag, util

# Helper for DAI types
if TYPE_CHECKING:
	RgbSensorResolution = dai.ColorCameraProperties.SensorResolution
	MonoSensorResolution = dai.MonoCameraProperties.SensorResolution
else:
	RgbSensorResolution = util.wrap_dai_enum(dai.ColorCameraProperties.SensorResolution)
	MonoSensorResolution = util.wrap_dai_enum(dai.MonoCameraProperties.SensorResolution)

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

S = TypeVar('S', bound=str)
class StageBase(BaseModel, Generic[S], ABC):
	infer: ClassVar[bool] = False
	merge: ClassVar[bool] = False

	stage: S = Field(description="Stage name")
	enabled: bool = Field(default=True, description="Is this stage enabled?")
	optional: bool = Field(default=False, description="If there's an error constructing this stage, is that a pipeline failure?")

	@property
	def name(self):
		if (target := getattr(self, 'target', None)) is not None:
			return f'{self.stage}.{target}'
		return self.stage

def _stage_base(name: S, *, merge: bool = False, implicit: bool = False):
	_merge = merge
	_S: S = S
	if not TYPE_CHECKING:
		_S = Literal[name]
	
	class _ModelHelper(StageBase[S], ABC):
		merge: ClassVar[bool] = _merge
		infer: ClassVar[bool] = implicit
		# Use default_factory to exclude default JSON
		stage: _S = Field(description="Stage name", default_factory=lambda: name)
	
	return _ModelHelper

class InheritStage(_stage_base('inherit')):
	"Include another defined pipeline"
	id: str

class RgbConfigStage(_stage_base('rgb', merge=True, implicit=True)):
	resolution: RgbSensorResolution | None = Field(default=None, description="Camera sensor resolution")
	fps: float | None = Field(default=None, description='Max FPS')


class MonoConfigStage(_stage_base('mono', implicit=True)):
	"Configure mono camera"
	target: Literal["left", "right"]
	resolution: MonoSensorResolution | None = Field(default=None, description='Camera sensor resolution')
	fps: float | None = Field(default=None, description='Max FPS')
	

class DepthConfigStage(_stage_base('depth')):
	"Configure stereo depth"
	checkLeftRight: bool | None = Field(default=None, description="Enable Left-Right check")
	extendedDisparity: bool | None = Field(default=None, description="Enable extended disparity mode")
	preset: Literal[
		'high_accuracy',
		'high_density',
		None,
	] = Field(default=None, description='Set preset profile')


class ObjectDetectionStage(_stage_base("nn")):
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

class WebStreamStage(_stage_base("web")):
	"Stream data to web"
	target: VideoDisplayTarget
	maxFramerate: Optional[int] = Field(None, gt=0, description="Maximum framerate for stream")
	@property
	def name(self):
		return f'{self.stage}.{self.target}'

class SaveStage(_stage_base("save")):
	"Save images to file"
	target: VideoDisplayTarget
	path: Path
	maxFramerate: Optional[float] = Field(default=None, gt=0, description="Maximum framerate for stream")

class ShowStage(_stage_base('show')):
	"Show video stream as GUI"
	target: VideoDisplayTarget

class ApriltagBase(_stage_base('apriltag')):
	runtime: Literal["device", "host"] = Field("host")
	camera: Literal["left", "right", "rgb"] = Field("left")

	# AprilTag detector runtime
	detectorThreads: int | None = Field(default=None, ge=0, description="How many threads should be used for computation")
	detectorAsync: bool = Field(False, description="Should we run the detector on a different thread? Only useful if we're doing multiple things with the same camera")

	# AprilTag detector params
	decodeSharpening: float | None = Field(default=None, ge=0, description="How much sharpening should be done to decoded images")
	quadDecimate: int = Field(1)
	quadSigma: float = Field(0.0)
	refineEdges: bool = Field(True)
	# Filter
	hammingDist: int = Field(default=0, ge=0, lt=3, description="Maximum number of bits to correct")
	decisionMargin: int = Field(35)

	# Pose
	numIterations: int = Field(40)
	undistort: bool = Field(False, description="Should we try to undistort the camera lens?")
	solvePNP: bool = Field(True)
	doMultiTarget: bool = Field(False)
	doSingleTargetAlways: bool = Field(False)

class ApriltagStage(ApriltagBase):
	apriltags: apriltag.AprilTagField

class ApriltagStageWorker(ApriltagBase):
	apriltags: apriltag.AprilTagFieldInlineWpi


class SlamStage(_stage_base('slam')):
	"SAI slam"
	slam: bool = Field(default=True)
	vio: bool = Field(default=False, description="Enable VIO")
	map_save: Optional[Path] = Field(default=None)
	map_load: Optional[Path] = Field(default=None)
	apriltags: Union[apriltag.AprilTagFieldRef, apriltag.AprilTagFieldInline, None] = Field(None)

class SlamStageWorker(SlamStage):
	apriltags: Optional[apriltag.AprilTagFieldRefSai]

class TelemetryStage(_stage_base('telemetry')):
	pass

class ImuStage(_stage_base('imu')):
	pass

PipelineStage = Annotated[
	Union[
		Annotated[InheritStage, Tag("inherit")],
		Annotated[RgbConfigStage, Tag("rgb")],
		Annotated[MonoConfigStage, Tag("mono")],
		Annotated[DepthConfigStage, Tag("depth")],
		Annotated[ObjectDetectionStage, Tag("nn")],
		Annotated[ApriltagStage, Tag("apriltag")],
		Annotated[SlamStage, Tag("slam")],
		Annotated[WebStreamStage, Tag("web")],
		Annotated[SaveStage, Tag("save")],
		Annotated[ShowStage, Tag("show")],
		Annotated[ImuStage, Tag("imu")],
	],
	Discriminator("stage")
]

PipelineStageWorker = Annotated[
	Union[
		# Annotated[InheritStage, Tag("inherit")],
		Annotated[RgbConfigStage, Tag("rgb")],
		Annotated[MonoConfigStage, Tag("mono")],
		Annotated[DepthConfigStage, Tag("depth")],
		Annotated[ObjectDetectionStage, Tag("nn")],
		Annotated[ApriltagStageWorker, Tag("apriltag")],
		Annotated[SlamStageWorker, Tag("slam")],
		Annotated[WebStreamStage, Tag("web")],
		Annotated[SaveStage, Tag("save")],
		Annotated[ShowStage, Tag("show")],
		Annotated[ImuStage, Tag("imu")],
	],
	Discriminator("stage")
]

PipelineConfig = RootModel[list[PipelineStage]]
PipelineConfigWorker = RootModel[list[PipelineStageWorker]]