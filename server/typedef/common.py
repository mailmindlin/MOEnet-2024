from typing import List, Dict, Literal, Optional
from pydantic import BaseModel, Field
from .wpilib_compat import FieldLayoutJSON, FieldTagJSON

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
    field: FieldLayoutJSON
    tags: List[FieldTagJSON]

class SlamConfigBase(BaseModel):
	"Configure SLAM settings"
	backend: Literal["sai"] = Field("sai")
	syncNN: bool = False
	slam: bool = True
	vio: bool = Field(False, description="Enable VIO")
	debugImage: bool = False
	debugImageRate: Optional[int] = None

class OakSelector(BaseModel):
	ordinal: Optional[int] = Field(None, description="Pick the nth camera found (unstable, starts at 1)", ge=1)
	mxid: Optional[str] = Field(None, description="Filter camera by mxid")
	name: Optional[str] = Field(None, description="Device name")
	platform: Optional[Literal["X_LINK_ANY_PLATFORM", "X_LINK_MYRIAD_2", "X_LINK_MYRIAD_X"]] = Field(None)
	protocol: Optional[Literal["X_LINK_ANY_PROTOCOL", "X_LINK_IPC", "X_LINK_NMB_OF_PROTOCOLS", "X_LINK_PCIE", "X_LINK_TCP_IP", "X_LINK_USB_CDC", "X_LINK_USB_VSC"]] = Field(None)