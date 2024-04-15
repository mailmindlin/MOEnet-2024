from datetime import timedelta
from enum import Enum, auto
import dataclasses
import numpy as np

from estimator.observation import DataSource
from estimator.tf import ReferenceFrame
from .util.replay import ReplayableFilter
from util.timestamp import Timestamp
from typedef.geom import Twist2d, Pose2d, Rotation2d
from .observation import Observation, PoseEstimator, PoseObservation
from .util.interpolated import InterpolatingBuffer
from datetime import timedelta

@dataclasses.dataclass
class OdometryMeasurement:
	ts: Timestamp
	twist: Twist2d
	gyroAngle: Rotation2d | None = None

@dataclasses.dataclass
class VisionMeasurement:
	ts: Timestamp
	pose: Pose2d

@dataclasses.dataclass
class Snapshot:
	ts: Timestamp
	pose: Pose2d

class SensorMode(Enum):
	ABSOLUTE = auto()
	RELATIVE = auto()
	DIFFERENTIAL = auto()


class WpiPoseEstimatorInner(ReplayableFilter[OdometryMeasurement | VisionMeasurement, Snapshot]):
	def __init__(self):
		super().__init__()
		self.state = Snapshot(
			ts=Timestamp.invalid(),
			pose=Pose2d(),
		)
		qStdDevs = np.array([0.03, 0.03, 0.03], dtype=float)
		self.q = np.diag(np.square(qStdDevs))

	def snapshot(self) -> Snapshot:
		return dataclasses.replace(self.state)
	
	def restore(self, state: Snapshot):
		self.state = dataclasses.replace(state)
	
	def observe(self, measurement: OdometryMeasurement | VisionMeasurement):
		if isinstance(measurement, OdometryMeasurement):
			pass
	
	def predict(self, now: Timestamp, delta: timedelta):
		pass

@dataclasses.dataclass
class WpiDataSource:
	name: str
	frame: ReferenceFrame
	mode: SensorMode = SensorMode.ABSOLUTE
	last_data: Timestamp | None = None
	first_pose: Pose2d | None = None
	last_pose: Pose2d | None = None

class WpiPoseEstimator(PoseEstimator[Observation, WpiDataSource]):
	def __init__(self) -> None:
		self._sources: dict[str, WpiDataSource] = dict()
		

	def get_source(self, name: str, frame: ReferenceFrame, mode: SensorMode = SensorMode.ABSOLUTE) -> WpiDataSource:
		if cached := self._sources.get(name, None):
			if cached.frame == frame and cached.mode == mode:
				return cached
		res = WpiDataSource(name, frame, mode)
		self._sources[name] = res
		return res
	
	def _observe_pose(self, source: WpiDataSource, base: ReferenceFrame, target: ReferenceFrame, pose: Pose2d):
		pass
	
	def observe(self, source: WpiDataSource, ts: Timestamp, value: Observation):
		assert self._sources[source.name] == source
		if isinstance(value, PoseObservation):
			if value.base_frame == ReferenceFrame.FIELD:
				if source.frame == ReferenceFrame.ODOM:
					# Odometry data