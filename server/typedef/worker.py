"""
Type definitions for communicating between the master and worker processes
"""

from typing import Optional, List, Any, Literal, Union, TypeAlias
from enum import IntEnum
from pydantic import BaseModel, Field

from .common import NNConfig, SlamConfigBase, OakSelector
from .geom import Pose3d, Translation3d, Twist3d, Transform3d

class ObjectDetectionConfig(NNConfig):
    "Configure an object detection pipeline"
    blobPath: str

class SlamConfig(SlamConfigBase):
    apriltagPath: Optional[str] = None

class InitConfig(BaseModel):
    "Config for worker.main"
    id: Optional[str]
    selector: OakSelector
    max_usb: Optional[Literal["FULL", "HIGH", "LOW", "SUPER", "SUPER_PLUS", "UNKNOWN"]]
    optional: bool = Field(False)
    outputRGB: bool = Field(False)
    maxRefresh: float = Field(5)
    robot_to_camera: Transform3d
    slam: Optional[SlamConfig]
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
    pose: Pose3d

class CmdFlush(BaseModel):
    id: int

class CmdChangeState(BaseModel):
    target: WorkerState

class MsgChangeState(BaseModel):
    previous: Optional[WorkerState]
    current: WorkerState

class MsgFlush(BaseModel):
    id: int

class MsgDetection(BaseModel):
    label: str
    confidence: float
    position: Translation3d

class MsgDetections(BaseModel):
    timestamp: int
    detections: List[MsgDetection]

    def __iter__(self):
        return iter(self.detections)

class MsgPose(BaseModel):
    timestamp: int
    "Timestamp (nanoseconds, in adjusted-local time)"
    view_mat: Any
    pose: Pose3d
    "Field-to-camera pose"
    poseCovariance: Any
    twist: Twist3d
    "Field-to-camera twist"
    twistCovariance: Any

AnyCmd = Union[CmdPoseOverride, CmdFlush, CmdChangeState]
AnyMsg = Union[MsgChangeState, MsgFlush, MsgDetections, MsgPose]