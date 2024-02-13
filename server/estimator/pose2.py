from typing import Optional
import logging, enum
import numpy as np

from wpimath.interpolation._interpolation import TimeInterpolatablePose3dBuffer
from wpiutil.log import DataLog, DoubleArrayLogEntry, DoubleLogEntry

from worker.msg import MsgPose, AprilTagPose
from typedef.cfg import PoseEstimatorConfig, AprilTagStrategy
from wpi_compat.datalog import StructLogEntry
from typedef.geom import Transform3d, Pose3d, Translation3d, Rotation3d, Twist3d
from typedef.geom_cov import Pose3dCov, Twist3dCov
from util.clock import Clock, WallClock
from util.timestamp import Timestamp
from .util import interpolate_pose3d


class SensorMode(enum.Enum):
    ABSOLUTE = enum.auto()
    "Pose data is absolute relative to the field"
    RELATIVE = enum.auto()
    "Pose data is in a fixed (but unaligned) reference frame"
    DIFFERENTIAL = enum.auto()
    "Pose data is in a floating reference frame"


class DataSource:
    name: str
    last_timestamp: Timestamp
    def __init__(self, name: str, src_to_robot: Transform3d):
        self.name = name
        self.src_to_robot = src_to_robot
        self.last_timestamp = WallClock().now()
        self.last_pose = None
        self.last_twist = None
    
    def get_correction(self) -> Transform3d:
        pass

    def observe(self, time: Timestamp, *, pose: Pose3d | Pose3dCov | None = None, twist: Twist3d | Twist3dCov | None = None):
        pass

class KalmanFilter:
    def __init__(self, _state, _ip):
        '''
        The matrices of Kalman filter:
        System:
        next_state = A*prev_state + B*input
        output = C*next+state + D*input
        '''
        self.state = _state
        self.ip = _ip
        self.output = None
        self.A = None
        self.B = None
        self.C = None
        self.D = None
        self.SigmaState=None
        self.SigmaOutput = None
        self.P = None
    
    def set_kalman_matrices(self, A, B, C, D, P, SigmaState, SigmaOutput):
        self.A = A
        self.B = B
        self.C = C
        self.D = D
        self.SigmaState= SigmaState
        self.SigmaOutput = SigmaOutput
        self.P = P
    
    def predict(self, state):
        self.state = next_state(self.state, self.ip) + np.random.normal([1,1,0], [0.4, 0.4, 0.001], 3)
        self.P = self.A*self.P*np.transpose(A) + self.SigmaState
        self.output = C.dot(self.state)
        return self.state

    def estimate(self, measurement):
        Kalman_gain = self.P*np.transpose(C) * np.linalg.pinv((C*self.P*np.transpose(C) + SigmaOutput))
        gain_factor = Kalman_gain.dot((measurement - self.output))
        self.state = self.state + gain_factor
        self.P = (np.diag([1,1,1]) - Kalman_gain*self.C)*self.P
        self.output = C.dot(self.state)

        return self.state, self.output 



def next_state(prev_state, ip):
    x_next = prev_state[0] + ip[0] * np.arccos(prev_state[2])
    y_next = prev_state[1] + ip[0] * np.arccos(prev_state[2])
    theta_next = prev_state[2] + ip[1]

    return np.transpose(np.array([x_next, y_next, theta_next]))

class PoseEstimator2:
    def __init__(self, config: PoseEstimatorConfig, clock: Clock, *, log: logging.Logger, datalog: Optional[DataLog] = None) -> None:
        self.frames = dict()

    def record_absolute(self, timestamp: Timestamp, pose: Pose3d):
        pass

    def get_frame(self, name: str, robot_to_sensor: Transform3d, mode: SensorMode = SensorMode.RELATIVE) -> DataSource:
        pass

    def predict(self, state):
        self.state = next_state(self.state, self.ip) + np.random.normal([1,1,0], [0.4, 0.4, 0.001], 3)
        self.P = self.A*self.P*np.transpose(A) + self.SigmaState
        self.output = C.dot(self.state)
        return self.state

    def estimate(self, measurement):
        Kalman_gain = self.P*np.transpose(C) * np.linalg.pinv((C*self.P*np.transpose(C) + SigmaOutput))
        gain_factor = Kalman_gain.dot((measurement - self.output))
        self.state = self.state + gain_factor
        self.P = (np.diag([1,1,1]) - Kalman_gain*self.C)*self.P
        self.output = C.dot(self.state)

        return self.state, self.output 