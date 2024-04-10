from dataclasses import dataclass
from util.timestamp import Timestamp
from .se3 import Pose3dCov, Twist3dCov
@dataclass
class Odometry:
	stamp: Timestamp
	pose: Pose3dCov
	twist: Twist3dCov

	def isfinite(self):
		return self.pose.isfinite() and self.twist.isfinite()