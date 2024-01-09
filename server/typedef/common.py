from typing import List, Dict, Literal, Optional, TypedDict
from pydantic import BaseModel, Field

class FieldLayoutJSON(TypedDict):
    length: float
    "Field length (meters)"
    width: float
    "Field width (meters)"

class Translation3dJSON(TypedDict):
    x: float
    y: float
    z: float

class Quaternion3dJSON(TypedDict):
    W: float
    X: float
    Y: float
    Z: float

class Rotation3dJSON(TypedDict):
    quaternion: Quaternion3dJSON

class Pose3dJSON(TypedDict):
    translation: Translation3dJSON
    rotation: Rotation3dJSON

class FieldTagJSON(BaseModel):
    ID: int
    pose: Pose3dJSON

class AprilTagFieldJSON(BaseModel):
    field: FieldLayoutJSON
    tags: List[FieldTagJSON]

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
	name: Optional[str]
	platform: Optional[Literal["X_LINK_ANY_PLATFORM", "X_LINK_MYRIAD_2", "X_LINK_MYRIAD_X"]]
	protocol: Optional[Literal["X_LINK_ANY_PROTOCOL", "X_LINK_IPC", "X_LINK_NMB_OF_PROTOCOLS", "X_LINK_PCIE", "X_LINK_TCP_IP", "X_LINK_USB_CDC", "X_LINK_USB_VSC"]]