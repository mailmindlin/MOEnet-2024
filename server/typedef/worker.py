"""
Type definitions for communicating between the master and worker processes
"""

from typing import Optional, List, Any, Literal, Union, TypeAlias
from enum import IntEnum
from pydantic import BaseModel, Field

from .geom import Pose, Vector3, Twist
from .common import NNConfig, SlamConfigBase, OakSelector

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
    pose: Pose
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
    pose: Pose

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
    position: Vector3

class MsgDetections(BaseModel):
    timestamp: int
    detections: List[MsgDetection]

    def __iter__(self):
        return iter(self.detections)

class MsgPose(BaseModel):
    timestamp: int
    view_mat: Any
    pose: Pose
    poseCovariance: Any
    twist: Twist
    twistCovariance: Any

AnyCmd = Union[CmdPoseOverride, CmdFlush, CmdChangeState]
AnyMsg = Union[MsgChangeState, MsgFlush, MsgDetections, MsgPose]