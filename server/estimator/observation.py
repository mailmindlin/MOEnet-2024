from typing import TypeAlias, Union

from util.timestamp import Timestamp
from typedef.geom import Pose3d

class ObservationBase:
    ts: Timestamp
    is_control: bool = False
    
    def __init__(self, ts: Timestamp) -> None:
        self.ts = ts

class PoseOverrideObservation(ObservationBase):
    "Pose override from Rio"
    pose: Pose3d
    is_control: bool = True
    def __init__(self, ts: Timestamp, pose: Pose3d) -> None:
        super().__init__(ts)
        self.pose = pose


class OdometryObservation(ObservationBase):
    "Rio odometry"
    pass

class SlamObservation(ObservationBase):
    "Camera SLAM"
    pass

class AprilTagObservation(ObservationBase):
    "Camera AprilTag"
    pass

class ObjectDetectionObservation(ObservationBase):
    "Object detection"
    

Observation: TypeAlias = Union[
    PoseOverrideObservation,
    OdometryObservation,
    SlamObservation,
    AprilTagObservation,
]

class PoseEstimator:
    def observe(self, observation: Observation):
        pass