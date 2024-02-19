"""
Type definitions for communicating between the master and worker processes
"""

from typing import Optional, Any, Literal, Union, TypeAlias
from enum import IntEnum, auto
from pydantic import BaseModel, Field
from dataclasses import dataclass
import numpy as np

from typedef.common import OakSelector, RetryConfig
from typedef.geom import Pose3d, Translation3d, Twist3d, Transform3d
from typedef.geom_cov import Pose3dCov, Twist3dCov
from typedef.pipeline import PipelineStageWorker

Mat33 = np.ndarray[float, tuple[Literal[3], Literal[3]]]
Mat44 = np.ndarray[float, tuple[Literal[4], Literal[4]]]
Mat66 = np.ndarray[float, tuple[Literal[6], Literal[6]]]

class WorkerInitConfig(BaseModel):
    "Config for worker.main"
    name: str
    selector: OakSelector
    retry: RetryConfig
    max_usb: Literal["FULL", "HIGH", "LOW", "SUPER", "SUPER_PLUS", "UNKNOWN", None] = Field(None)
    maxRefresh: float = Field(10, description="Maximum polling rate (Hz)")
    robot_to_camera: Transform3d
    dynamic_pose: Optional[str] = Field(None)
    pipeline: list[PipelineStageWorker] = Field(default_factory=list)


class WorkerState(IntEnum):
    INITIALIZING = auto()
    CONNECTING = auto()
    "Worker is connecting to the camera"
    RUNNING = auto()
    "Running as expected"
    PAUSED = auto()
    FAILED = auto()
    STOPPING = auto()
    STOPPED = auto()

    

class CmdPoseOverride(BaseModel):
    "Override worker pose"
    pose: Pose3d
    "Pose (field-to-camera)"

class CmdFlush(BaseModel):
    "Request a data flush"
    id: int
    "Flush ID (for matching with MsgFlush)"

class CmdChangeState(BaseModel):
    target: WorkerState

class CmdEnableStream(BaseModel):
    "Request the worker enable the named stream"
    stream: str
    enable: bool

AnyCmd = Union[
    CmdPoseOverride,
    CmdFlush,
    CmdChangeState,
    CmdEnableStream,
]
"Commands to send to worker"


class MsgChangeState(BaseModel):
    "Notify the main process that the worker changed its state"
    previous: Optional[WorkerState]
    "Previous state"
    current: WorkerState
    "Current state"

class MsgFlush(BaseModel):
    "Notify that a flush was completed"
    id: int

@dataclass
class ObjectDetection:
    label: str
    confidence: float
    position: Translation3d

@dataclass
class AprilTagDetection:
    tag_family: str
    tag_id: int
    hamming: int
    decision_margin: float
    corners: np.ndarray[float, tuple[Literal[4], Literal[2]]]
    homography: Mat33

    def getFamily(self):
        return self.tag_family
    
    def getId(self):
        return self.tag_id
    def getHamming(self):
        return self.hamming
    def getDecisionMargin(self):
        return self.decision_margin
    def getCorners(self, *args):
        return self.corners


class MsgDetections(BaseModel):
    timestamp: int
    "Wall time (ns)"
    detections: list[ObjectDetection]

    def __iter__(self):
        return iter(self.detections)

class AprilTagPose(BaseModel):
    error: float
    camToTag: Transform3d
    fieldToCam: Pose3d | None


class MsgAprilTagPoses(BaseModel):
    timestamp: int
    poses: list[AprilTagPose]
    "Represents multiple possible poses"


@dataclass
class MsgPose:
    timestamp: int
    "Wall time (ns)"
    pose: Pose3d
    "Field-to-camera pose"
    poseCovariance: Mat66

@dataclass
class MsgOdom:
    timestamp: int
    "Wall time (ns)"
    pose: Pose3dCov
    "Field-to-camera pose"
    twist: Twist3dCov
    "Field-to-camera twist"

class MsgLog(BaseModel):
    level: int
    name: str
    msg: str

@dataclass
class MsgFrame:
    worker: str
    stream: str
    timestamp: int
    timestamp_recv: int
    sequence: int
    data: Any
    timestamp_insert: int = 0
    timestamp_extract: int = 0

WorkerMsg: TypeAlias = Union[
    MsgChangeState,
    MsgFlush,
    MsgDetections,
    MsgPose,
    MsgLog,
]
"Worker message types"

AnyMsg = Union[
    MsgDetections,
    MsgPose,
    MsgAprilTagPoses,
    MsgOdom,
]
"Public message types"