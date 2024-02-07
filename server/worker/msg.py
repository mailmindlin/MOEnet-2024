"""
Type definitions for communicating between the master and worker processes
"""

from typing import Optional, Any, Literal, Union
from enum import IntEnum
from pydantic import BaseModel, Field
from dataclasses import dataclass

from typedef.common import OakSelector, RetryConfig
from typedef.geom import Pose3d, Translation3d, Twist3d, Transform3d
from typedef.pipeline import PipelineStage, NNConfig

class ObjectDetectionConfig(NNConfig):
    "Configure an object detection pipeline"
    blobPath: str

class WorkerInitConfig(BaseModel):
    "Config for worker.main"
    id: str
    selector: OakSelector
    retry: RetryConfig
    max_usb: Literal["FULL", "HIGH", "LOW", "SUPER", "SUPER_PLUS", "UNKNOWN", None] = Field(None)
    maxRefresh: float = Field(10, description="Maximum polling rate (Hz)")
    robot_to_camera: Transform3d
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

AnyCmd = Union[CmdPoseOverride, CmdFlush, CmdChangeState, CmdEnableStream]


class MsgChangeState(BaseModel):
    "Notify the main process that the worker changed its state"
    previous: Optional[WorkerState]
    "Previous state"
    current: WorkerState
    "Current state"

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
    detections: list[MsgDetection]

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
]
"Public message types"