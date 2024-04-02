from datetime import timedelta
import dataclasses
import numpy as np
from .util.replay import ReplayableFilter
from util.timestamp import Timestamp
from typedef.geom import Twist2d, Pose2d

@dataclasses.dataclass
class OdometryMeasurement:
    ts: Timestamp
    twist: Twist2d

@dataclasses.dataclass
class VisionMeasurement:
    ts: Timestamp
    pose: Pose2d


@dataclasses.dataclass
class Snapshot:
    ts: Timestamp
    pose: Pose2d


class WpiPoseEstimatorInner(ReplayableFilter[OdometryMeasurement | VisionMeasurement, Snapshot]):
    def __init__(self):
        super().__init__()
        self.state = Snapshot(
            ts=None,
            pose=Pose2d(),
        )
        qStdDevs = np.array([0.03, 0.03, 0.03], dtype=float)
        self.q = np.diag(np.square(qStdDevs))

    def snapshot(self) -> Snapshot:
        return dataclasses.replace(self.state)
    
    def restore(self, state: Snapshot):
        self.state = dataclasses.replace(state)
    
    def observe(self, measurement: OdometryMeasurement | VisionMeasurement):
        pass
    
    def predict(self, now: Timestamp, delta: timedelta):
        pass

class WpiPoseEstimator:
    def __init__(self) -> None:
        pass

