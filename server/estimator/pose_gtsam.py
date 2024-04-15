from typing import Protocol

from estimator.observation import DataSource
from estimator.tf import ReferenceFrame
from gtsam import NonlinearISAM, NonlinearFactorGraph, Values
from gtsam.symbol_shorthand import X, L

from typedef.geom import Pose3d
from typedef.cfg import PoseEstimatorConfig
from util.timestamp import Timestamp
from .observation import Observation, PoseEstimator

class _NonlinearISAM(Protocol):
	def estimate(self): ...

class NonLinearEstimator(PoseEstimator[Observation]):
	"Pose estimator that uses GTSAM as a backend"
	
	def __init__(self, config: PoseEstimatorConfig):
		self.config = config
		
		self._isam = NonlinearISAM()
		self._graph = NonlinearFactorGraph()
		self._guesses = Values()
		self._pose_id = 0
		self._current_pose = Pose3d()

	def get_source(self, name: str, frame: ReferenceFrame) -> DataSource:
		return super().get_source(name, frame)
	
	def observe(self, source: DataSource, ts: Timestamp, value: Observation):
		if isinstance(value, PoseOverrideObservation):
			self._isam = NonlinearISAM()
			self._graph.clear()
			self._guesses.clear()
			self._current_pose = observation.pose
			