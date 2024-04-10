from typing import Literal, ClassVar
from dataclasses import dataclass

import numpy as np
from wpiutil import wpistruct
from .base import CovariantWrapper

@dataclass
class LinearAcceleration3d:
	x: wpistruct.double = 0
	y: wpistruct.double = 0
	z: wpistruct.double = 0

@dataclass
class AngularAcceleration3d:
	ax: wpistruct.double = 0
	ay: wpistruct.double = 0
	az: wpistruct.double = 0

class LinearAcceleration3dCov(CovariantWrapper[LinearAcceleration3d, Literal[3]]):
	STATE_LEN: ClassVar[int] = 3

	@classmethod
	def parse_numpy(cls, mean: LinearAcceleration3d | np.ndarray[tuple[Literal[3]], np.dtype[np.floating]]) -> LinearAcceleration3d:
		"Parse numpy array as datatype"
		if isinstance(mean, LinearAcceleration3d):
			return mean
		assert np.shape(mean) == (3,)
		return LinearAcceleration3d(
			mean[0],
			mean[1],
			mean[2],
		)
	
	def mean_vec(self) -> np.ndarray[tuple[Literal[3]], np.dtype[np.float64]]:
		return np.array([
			self.mean.x,
			self.mean.y,
			self.mean.z,
		], dtype=np.float64)

class Acceleration3d:
	linear: LinearAcceleration3d
	angular: AngularAcceleration3d

	def __init__(self, linear: LinearAcceleration3d | None = None, angular: AngularAcceleration3d | None = None):
		self.linear = linear or LinearAcceleration3d()
		self.angular = angular or AngularAcceleration3d()

class Acceleration3dCov(CovariantWrapper[Acceleration3d, Literal[6]]):
	STATE_LEN: ClassVar[int] = 6

	@classmethod
	def parse_numpy(cls, mean: Acceleration3d | np.ndarray[tuple[Literal[6]], np.dtype[np.floating]]) -> Acceleration3d:
		"Parse numpy array as datatype"
		if isinstance(mean, Acceleration3d):
			return mean
		assert np.shape(mean) == (6,)
		return Acceleration3d(
			LinearAcceleration3d(
				mean[0],
				mean[1],
				mean[2],
			),
			AngularAcceleration3d(
				mean[3],
				mean[4],
				mean[5],
			)
		)
	
	def mean_vec(self) -> np.ndarray[tuple[Literal[6]], np.dtype[np.float64]]:
		return np.array([
			self.mean.linear.x,
			self.mean.linear.y,
			self.mean.linear.z,
			self.mean.angular.ax,
			self.mean.angular.ay,
			self.mean.angular.az,
		], dtype=np.float64)