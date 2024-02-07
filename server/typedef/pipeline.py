"Pipeline stage configuration"

from typing import TYPE_CHECKING, Literal, Optional, Union, Annotated, TypeVar, Generic, ClassVar
from pydantic import BaseModel, Field, Tag, Discriminator, RootModel
from pathlib import Path
from enum import Enum
import depthai as dai

try:
	from . import apriltag, util
except ImportError:
	import apriltag, util


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
class StageBase(BaseModel, Generic[S]):
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

def stage_base(name: S, *, merge: bool = False, implicit: bool = False):
	_merge = merge
	S1 = S
	if not TYPE_CHECKING:
		S1 = Literal[name]
	class StageBaseSpec(StageBase[S]):
		merge: ClassVar[bool] = _merge
		infer: ClassVar[bool] = implicit
		stage: S1 = Field(description="Stage name", default_factory=lambda: name)
	
	return StageBaseSpec

class InheritStage(stage_base('inherit')):
	"Include another defined pipeline"
	id: str

RgbSensorResolution = util.wrap_dai_enum(dai.ColorCameraProperties.SensorResolution)
class RgbConfigStage(stage_base('rgb', merge=True, implicit=True)):
	resolution: RgbSensorResolution | None = Field(default=None, description="Camera sensor resolution")


MonoSensorResolution = util.wrap_dai_enum(dai.MonoCameraProperties.SensorResolution)
class MonoConfigStage(stage_base('mono', implicit=True)):
	"Configure mono camera"
	target: Literal["left", "right"]
	resolution: MonoSensorResolution | None = Field(default=None, description='Camera sensor resolution')
	fps: float | None = Field(default=None, description='Max FPS')
	

class DepthConfigStage(stage_base('depth')):
	"Configure stereo depth"
	checkLeftRight: bool | None = Field(default=None, description="Enable Left-Right check")
	extendedDisparity: bool | None = Field(default=None, description="Enable extended disparity mode")
	preset: Literal[
		'high_accuracy',
		'high_density',
		None,
	] = Field(default=None, description='Set preset profile')


class ObjectDetectionStage(stage_base("nn")):
	config: Union[NNConfig, Path]
	blobPath: Path

class WebStreamStage(stage_base("web")):
	"Stream data to web"
	target: Literal["left", "right", "rgb", "depth"]
	maxFramerate: Optional[int] = Field(None, gt=0, description="Maximum framerate for stream")
	@property
	def name(self):
		return f'{self.stage}.{self.target}'

class SaveStage(stage_base("save")):
	"Save images to file"
	target: Literal["left", "right", "rgb", "depth"]
	path: Path
	maxFramerate: Optional[int] = Field(default=None, gt=0, description="Maximum framerate for stream")

class ShowStage(stage_base('show')):
	target: Literal["left", "right", "rgb", "depth"]

class ApriltagBase(stage_base('apriltag')):
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
	undistort: bool = Field(False)
	solvePNP: bool = Field(True)
	doMultiTarget: bool = Field(False)
	doSingleTargetAlways: bool = Field(False)

class ApriltagStage(ApriltagBase):
	apriltags: Union[apriltag.AprilTagFieldRef, apriltag.InlineAprilTagField]

class ApriltagStageWorker(ApriltagBase):
	apriltags: apriltag.WpiInlineAprilTagField


class SlamStage(stage_base('slam')):
	"SAI slam"
	slam: bool = Field(default=True)
	vio: bool = Field(default=False, description="Enable VIO")
	map_save: Optional[Path] = Field(default=None)
	map_load: Optional[Path] = Field(default=None)
	apriltags: Union[apriltag.AprilTagFieldRef, apriltag.InlineAprilTagField, None] = Field(None)

class SlamStageWorker(SlamStage):
	apriltags: Optional[apriltag.SaiAprilTagFieldRef]

class TelemetryStage(stage_base('telemetry')):
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
	],
	Discriminator("stage")
]

PipelineConfig = RootModel[list[PipelineStage]]
PipelineConfigWorker = RootModel[list[PipelineStageWorker]]