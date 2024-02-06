from typing import Literal, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from datetime import timedelta
if TYPE_CHECKING:
	import depthai as dai

try:
	from .wpilib_compat import FieldLayout, FieldTag
except ImportError:
	from wpilib_compat import FieldLayout, FieldTag

class NNConfig(BaseModel):
	"Base config for NN"
	confidence_threshold: float
	iou_threshold: float
	labels: List[str]
	depthLowerThreshold: int
	depthUpperThreshold: int
	classes: int
	coordinateSize: int
	anchors: List[float]
	anchor_masks: Dict[str, List[int]]

class AprilTagFieldConfig(BaseModel):
    field: FieldLayout
    tags: List[FieldTag]

class PipelineConfigBase(BaseModel):
	"Configure video pipeline"
	backend: Literal["sai"] = Field("sai")
	syncNN: bool = False
	slam: bool = True
	vio: bool = Field(False, description="Enable VIO")
	debugRgb: bool = False
	debugLeft: bool = False
	debugRight: bool = False
	debugDepth: bool = False
	debugImageRate: Optional[int] = Field(None)
	apriltag_explicit: bool = Field(False)
	telemetry: bool = Field(False)


class RetryConfig(BaseModel):
	"Configure restart/retry logic"
	optional: bool = Field(False, description="Is it an error if this camera is not detected?")
	connection_tries: int = 1
	connection_delay: timedelta = timedelta(seconds=1)
	restart_tries: int = 2


class OakSelector(BaseModel):
	ordinal: Optional[int] = Field(None, description="Pick the nth camera found (unstable, starts at 1)", ge=1)
	mxid: Optional[str] = Field(None, description="Filter camera by mxid")
	name: Optional[str] = Field(None, description="Device name")
	platform: Literal["X_LINK_ANY_PLATFORM", "X_LINK_MYRIAD_2", "X_LINK_MYRIAD_X", None] = Field(None)
	protocol: Literal["X_LINK_ANY_PROTOCOL", "X_LINK_IPC", "X_LINK_NMB_OF_PROTOCOLS", "X_LINK_PCIE", "X_LINK_TCP_IP", "X_LINK_USB_CDC", "X_LINK_USB_VSC", None] = Field(None)

	@property
	def platform_dai(self) -> 'dai.XLinkPlatform':
		"Get platform as DepthAI type"
		raw = self.platform
		if raw is None:
			return None
		from depthai import XLinkPlatform
		return XLinkPlatform.__members__[raw]
	
	@property
	def protocol_dai(self) -> 'dai.XLinkProtocol':
		"Get platform as DepthAI type"
		raw = self.protocol
		if raw is None:
			return None
		from depthai import XLinkProtocol
		return XLinkProtocol.__members__[raw]
