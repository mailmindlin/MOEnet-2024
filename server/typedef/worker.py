"""
Type definitions for communicating between the master and worker processes
"""

from typing import Optional, List, Any, Literal, Union
from enum import IntEnum
from pydantic import BaseModel, Field

from .common import NNConfig, SlamConfigBase, OakSelector, RetryConfig
from .geom import Pose3d, Translation3d, Twist3d, Transform3d

class ObjectDetectionConfig(NNConfig):
    "Configure an object detection pipeline"
    blobPath: str

class WorkerSlamConfig(SlamConfigBase):
    apriltagPath: Optional[str] = None

class WorkerInitConfig(BaseModel):
    "Config for worker.main"
    id: Optional[str]
    selector: OakSelector
    retry: RetryConfig
    max_usb: Literal["FULL", "HIGH", "LOW", "SUPER", "SUPER_PLUS", "UNKNOWN", None] = Field(None)
    outputRGB: bool = Field(False)
    maxRefresh: float = Field(10, description="Maximum polling rate (Hz)")
    robot_to_camera: Transform3d
    slam: Optional[WorkerSlamConfig]
    object_detection: Optional[ObjectDetectionConfig]

class WorkerState(IntEnum):
    INITIALIZING = 0
    CONNECTING = 1
    RUNNING = 2
    PAUSED = 3
    FAILED = 4
    STOPPING = 5
    STOPPED = 6

class CmdPoseOverride(BaseModel):
    "Override worker pose"
    pose: Pose3d
    "Pose (field-to-camera)"

class CmdFlush(BaseModel):
    "Request a data flush"
    id: int

class CmdChangeState(BaseModel):
    target: WorkerState

AnyCmd = Union[CmdPoseOverride, CmdFlush, CmdChangeState]


class MsgChangeState(BaseModel):
    previous: Optional[WorkerState]
    current: WorkerState

class MsgFlush(BaseModel):
    "Notify that a flush was completed"
    id: int

class MsgDetection(BaseModel):
    label: str
    confidence: float
    position: Translation3d

class MsgDetections(BaseModel):
    timestamp: int
    "Wall time (ns)"
    detections: List[MsgDetection]

    def __iter__(self):
        return iter(self.detections)

class MsgPose(BaseModel):
    timestamp: int
    "Wall time (ns)"
    view_mat: Any
    pose: Pose3d
    "Field-to-camera pose"
    poseCovariance: Any
    twist: Twist3d
    "Field-to-camera twist"
    twistCovariance: Any

class MsgLog(BaseModel):
    level: int
    msg: str

AnyMsg = Union[MsgChangeState, MsgFlush, MsgDetections, MsgPose, MsgLog]