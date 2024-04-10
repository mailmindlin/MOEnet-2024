from typing import Literal, ClassVar, Union, Self
import numpy as np
from .base import LinearCovariantBase
from .multi import RandomNormal
from ..geom import Rotation2d, Translation2d

def rot2_to_mat(rotation: Rotation2d) -> np.ndarray[tuple[Literal[2], Literal[2]], np.dtype[np.float64]]:
	"Rotation2d into rotation matrix"
	c = rotation.cos()
	s = rotation.sin()
	return np.array([
		[c, s],
		[-s, c],
	], dtype=np.float64)

class Translation2dCov(LinearCovariantBase[Translation2d, Literal[2]]):
	STATE_LEN: ClassVar[int] = 2

	def mean_vec(self) -> np.ndarray[tuple[Literal[2]], np.dtype[np.floating]]:
		return np.asanyarray(self.mean.toVector(), dtype=np.float64)

	@property
	def x(self) -> RandomNormal:
		return RandomNormal(self.mean.x, self.cov[0,0])
	
	@property
	def y(self) -> RandomNormal:
		return RandomNormal(self.mean.y, self.cov[1,1])
	
	def __add__(self, other: Union[Translation2d, Self, np.ndarray[tuple[Literal[2]], np.dtype[np.floating]]]):
		if isinstance(other, Translation2d):
			return Translation2dCov(self.mean + other, self.cov)
		return super().__add__(other)
	
	def rotateBy(self, rotation: Rotation2d) -> 'Translation2dCov':
		mean = self.mean.rotateBy(rotation)
		rot = rot2_to_mat(rotation)
		cov = rot @ self.cov @ rot.T

		return Translation2dCov(mean, cov)
	
	def mahalanobisDistanceTo(self, other: Self | Translation2d) -> float:
		"Returns the Mahalanobis distance from this PDF to some other point"
		if isinstance(other, Translation2d):
			mean2 = other
			cov2 = np.zeros_like(self.cov)
		else:
			mean2 = other.mean
			cov2 = other.cov
		
		deltaX = (mean2 - self.mean).toVector()
		return np.sqrt(deltaX.T @ np.linalg.inv(self.cov + cov2) @ deltaX)