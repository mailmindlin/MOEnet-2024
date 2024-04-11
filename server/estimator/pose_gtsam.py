from typing import Protocol

from gtsam import NonlinearISAM, NonlinearFactorGraph, Values
from gtsam.symbol_shorthand import X, L

from typedef.geom import Pose3d
from typedef.cfg import PoseEstimatorConfig
from .observation import Observation, PoseEstimator, PoseOverrideObservation

class _NonlinearISAM(Protocol):
	def estimate(self): ...

class NonLinearEstimator(PoseEstimator):
	"Pose estimator that uses GTSAM as a backend"
	
	def __init__(self, config: PoseEstimatorConfig):
		self.config = config
		
		self._isam = NonlinearISAM()
		self._graph = NonlinearFactorGraph()
		self._guesses = Values()
		self._pose_id = 0
		self._current_pose = Pose3d()
	
	def observe(self, observation: Observation):
		if isinstance(observation, PoseOverrideObservation):
			self._isam = NonlinearISAM()
			self._graph.clear()
			self._guesses.clear()
			self._current_pose = observation.pose
			