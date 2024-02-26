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
from typedef.pipeline import PipelineConfigWorker

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
    pipeline: PipelineConfigWorker = Field(default_factory=PipelineConfigWorker)


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

    # We define these functions to comply with the shape of `robotpy_apriltag.AprilTagDetection``
    def getFamily(self) -> str:
        "Gets the decoded tag's family name."
        return self.tag_family
    def getId(self) -> int:
        "Gets the decoded ID of the tag."
        return self.tag_id
    def getHamming(self) -> int:
        "Gets how many error bits were corrected"
        return self.hamming
    def getDecisionMargin(self) -> float:
        """
        Gets a measure of the quality of the binary decoding process: the
        average difference between the intensity of a data bit versus
        the decision threshold. Higher numbers roughly indicate better
        decodes. This is a reasonable measure of detection accuracy
        only for very small tags-- not effective for larger tags (where
        we could have sampled anywhere within a bit cell and still
        gotten a good detection.)
        """
        return self.decision_margin
    def getCorners(self, *args):
        """
        Gets the corners of the tag in image pixel coordinates. These always
        wrap counter-clock wise around the tag. The first set of corner coordinates
        are the coordinates for the bottom left corner.
        """
        return self.corners


class MsgDetections(BaseModel):
    timestamp: int
    "Wall time (ns)"
    detections: list[ObjectDetection]

    def __iter__(self):
        return iter(self.detections)

@dataclass
class PnpPose:
    error: float
    fieldToCam: Pose3d

@dataclass
class PnPResult:
    tags: set[int]
    poses: list[PnpPose]
    ambiguity: float = 0

    @property
    def best(self):
        return min(self.poses, key=lambda pose: pose.error)


class AprilTagPose(BaseModel):
    error: float
    camToTag: Transform3d
    fieldToCam: Pose3d | None

class MsgAprilTagDetections(BaseModel):
    timestamp: int
    detections: list[AprilTagPose] = Field(default_factory=list)
    pnp: PnPResult | None = Field(None)


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
    MsgAprilTagDetections,
    MsgOdom,
]
"Public message types"