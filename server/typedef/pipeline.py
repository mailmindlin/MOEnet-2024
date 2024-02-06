from typing import Literal, Optional, Union, Annotated
from pydantic import BaseModel, Field, Tag, Discriminator, RootModel
from pathlib import Path

try:
	from . import apriltag
except ImportError:
	import apriltag


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


class StageBase(BaseModel):
	stage: str
	enabled: bool = Field(True)
	optional: bool = Field(False)

	@property
	def name(self):
		return self.stage

class InheritStage(StageBase):
	stage: Literal["inherit"]
	id: str

class RgbConfigStage(StageBase):
	stage: Literal['rgb']

class MonoConfigStage(StageBase):
	stage: Literal['mono']
	target: Literal["left", "right"]
	@property
	def name(self):
		return f'{self.stage}.{self.target}'

class DepthConfigStage(StageBase):
	stage: Literal['depth']

class ObjectDetectionStage(StageBase):
	stage: Literal["nn"]
	config: Union[NNConfig, Path]
	blobPath: Path

class WebStreamStage(StageBase):
	stage: Literal['web']
	target: Literal["left", "right", "rgb", "depth"]
	maxFramerate: Optional[int] = Field(None, gt=0, description="Maximum framerate for stream")
	@property
	def name(self):
		return f'{self.stage}.{self.target}'

class SaveStage(StageBase):
	stage: Literal['save']
	target: Literal["left", "right", "rgb", "depth"]
	path: Path
	maxFramerate: Optional[int] = Field(None, gt=0, description="Maximum framerate for stream")

class ShowStage(StageBase):
	stage: Literal['show']
	target: Literal["left", "right", "rgb", "depth"]

class ApriltagStage(StageBase):
	stage: Literal["apriltag"]
	runtime: Literal["device", "host"] = Field("host")
	camera: Literal["left", "right", "rgb"] = Field("left")
	apriltags: Union[apriltag.AprilTagFieldRef, apriltag.InlineAprilTagField]

	quadDecimate: int = Field(1)
	quadSigma: float = Field(0.0)
	refineEdges: bool = Field(True)
	numIterations: int = Field(40)
	hammingDist: int = Field(0)
	decisionMargin: int = Field(35)

class ApriltagStageWorker(ApriltagStage):
	apriltags: apriltag.WpiInlineAprilTagField


class SlamStage(StageBase):
	"SAI slam"
	stage: Literal['slam']
	slam: bool = Field(True)
	vio: bool = Field(False, description="Enable VIO")
	map_save: Optional[str] = Field(None)
	map_load: Optional[str] = Field(None)
	apriltags: Union[apriltag.AprilTagFieldRef, apriltag.InlineAprilTagField, None] = Field(None)

class SlamStageWorker(SlamStage):
	apriltags: Optional[apriltag.SaiAprilTagFieldRef]

class TelemetryStage(StageBase):
	stage: Literal["telemetry"]

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