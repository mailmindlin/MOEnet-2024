from typing import overload, TypeVar, Generic, Literal
from dataclasses import dataclass

import numpy as np
from numpy import ndarray
from scipy.spatial.transform import Rotation

from .geom import (
	Translation2d, Translation3d,
	Twist2d, Twist3d,
	Rotation2d, Rotation3d,
	Transform2d, Transform3d,
	Pose2d, Pose3d,
	Quaternion
)
from util.timestamp import Timestamp
from wpiutil import wpistruct

def rot2_to_mat(rotation: Rotation2d) -> np.ndarray[float, tuple[Literal[2], Literal[2]]]:
	"Rotation2d into rotation matrix"
	c = rotation.cos()
	s = rotation.sin()
	return np.array([
		[c, s],
		[-s, c],
	], dtype=float)

def rot3_to_mat(rotation: Rotation3d) -> np.ndarray[float, tuple[Literal[3], Literal[3]]]:
	"Rotation3d into rotation matrix"
	i, j, k, w = rotation.X(), rotation.Y(), rotation.Z(), rotation.W()

	# create rotation matrix
	r = Rotation.from_quat([i, j, k, w])
	return r.as_matrix()

def rot3_to_mat6(rotation: Rotation3d) -> np.ndarray[float, tuple[Literal[6], Literal[6]]]:
	"Make 6d-rotation matrix"
	rmat = rot3_to_mat(rotation)
	rot6d = np.eye((6, 6), dtype=float)
	rot6d[:3,:3] = rmat
	rot6d[3:,3:] = rmat
	return rot6d

def rot3_flatten(rotation: Rotation3d) -> Rotation3d:
	yaw = rotation.Z()
	return Rotation3d(0, 0, yaw)


T = TypeVar('T')
N = TypeVar('N', bound=int)

class Covariant(Generic[N]):
	STATE_LEN: int = 0
	cov: np.ndarray[float, tuple[N, N]]
	"Covariance matrix"
	def __init__(self, cov: np.ndarray[float, tuple[N, N]] | None = None) -> None:
		super().__init__()
		if cov is None:
			cov = np.zeros((self.STATE_LEN, self.STATE_LEN), dtype=float)
		assert cov.shape == (self.STATE_LEN, self.STATE_LEN)
		self.cov = cov
	
	def isfinite(self):
		return np.isfinite(self.mean_vec()) and np.isfinite(self.cov)
	
	def mean_vec(self) -> np.ndarray[float, N]:
		"Get mean, as numpy array"
		pass


class CovariantWrapper(Covariant[N], Generic[T, N]):
	@classmethod
	def parse_numpy(cls, mean: T | np.ndarray[float, N]) -> T:
		"Parse numpy array as datatype"
		return mean
	
	def __init__(self, mean: T | np.ndarray[float, N], cov: np.ndarray[float, tuple[N, N]] | None = None):
		super().__init__(cov)
		self.mean = type(self).parse_numpy(mean)
	
	@overload
	def sample(self) -> T:
		"Sample a single possible value from this distribution"
		...
	@overload
	def sample(self, n: int) -> list[T]:
		"Sample multiple values from this distribution"
		...
	def sample(self, n: int | None = None):
		mean_np = self.mean_vec()
		sample = np.random.multivariate_normal(mean_np, self.cov, n)
		if n is None:
			return type(self).parse_numpy(sample)
		else:
			return [
			type(self).parse_numpy(sample[i])
			for i in range(n)
		]
	
	def __matmul__(self, tf: np.ndarray[float, N]):
		pass


class Translation2dCov(CovariantWrapper[Translation2d, Literal[2]]):
	STATE_LEN = 2
	def rotateBy(self, rotation: Rotation2d) -> 'Translation2dCov':
		mean = self.mean.rotateBy(rotation)
		rot = rot2_to_mat(rotation)
		cov = rot @ self.cov @ rot.T

		return Translation2dCov(mean, cov)

	def mean_vec(self) -> np.ndarray[float, Literal[2]]:
		return np.array([
			self.mean.x,
			self.mean.y,
		], dtype=float)

class Translation3dCov(CovariantWrapper[Translation3d, Literal[3]]):
	STATE_LEN = 3
	def rotateBy(self, rotation: Rotation3d) -> 'Translation3dCov':
		mean = self.mean.rotateBy(rotation)
		rot = rot3_to_mat(rotation)
		cov = rot @ self.cov @ rot.T
		return Translation3dCov(mean, cov)

	def mean_vec(self) -> np.ndarray[float, Literal[3]]:
		return np.array([
			self.mean.x,
			self.mean.y,
			self.mean.z,
		], dtype=float)

class Pose3dQuatCov(CovariantWrapper[Pose3d, Literal[7]]):
	STATE_LEN = 7
	
	@classmethod
	def parse_numpy(cls, mean: Pose3d | np.ndarray[float, Literal[7]]) -> Pose3d:
		"Parse numpy array as datatype"
		if isinstance(mean, Pose3d):
			return mean
		assert np.shape(mean) == (7,)
		return Pose3d(
			Translation3d(
				mean[0],
				mean[1],
				mean[2],
			),
			Rotation3d(
				Quaternion(
					mean[3],
					mean[4],
					mean[5],
					mean[6],
				)
			)
		)
	
	def inverse(self) -> 'Pose3dQuatCov':
		# https://github.com/MRPT/mrpt/blob/4c9da0fb51e50148d28c46964bd698688c727f47/libs/poses/src/CPose3DQuatPDFGaussian.cpp#L281
		raise NotImplementedError()

	def mean_vec(self) -> ndarray[float, Literal[7]]:
		quat = self.mean.rotation().getQuaternion()
		return np.array([
			self.mean.x,
			self.mean.y,
			self.mean.z,
			quat.X(),
			quat.Y(),
			quat.Z(),
		])

class Pose3dCov(CovariantWrapper[Pose3d, Literal[6]]):
	STATE_LEN = 6
	@classmethod
	def parse_numpy(cls, mean: Pose3d | np.ndarray[float, Literal[6]]) -> Pose3d:
		"Parse numpy array as datatype"
		if isinstance(mean, Pose3d):
			return mean
		assert np.shape(mean) == (6,)
		return Pose3d(
			Translation3d(
				mean[0],
				mean[1],
				mean[2],
			),
			Rotation3d(
				mean[3],
				mean[4],
				mean[5],
			)
		)
	
	@property
	def rotation(self):
		return self.mean.rotation()
	@property
	def translation(self):
		return Translation3dCov(
			mean=self.mean.translation(),
			cov=self.cov[:3, :3],
		)
	
	def inverse(self) -> 'Pose3dCov':
		# This is like: b=(0,0,0)
		#  OUT = b - THIS
		zero = Pose3dCov(Pose3d(), np.zeros_like(self.cov))
		return zero - self
	
	def mean_vec(self) -> np.ndarray[float, Literal[6]]:
		rot = self.mean.rotation()
		return np.array([
			self.mean.x,
			self.mean.y,
			self.mean.z,
			rot.X(),
			rot.Y(),
			rot.Z(),
		])

	def transformBy(self, tf: Transform3d) -> 'Pose3dCov':
		rot = rot3_to_mat6(tf.rotation())
		cov_rotated = rot @ self.cov @ rot.T
		return Pose3dCov(
			self.mean.transformBy(tf),
			cov_rotated
		)
	
	def transformCov(self, tf: Rotation3d | Transform3d) -> 'Pose3dCov':
		if isinstance(tf, Transform3d):
			rot = tf.rotation()
		else:
			rot = tf
		rot6d = rot3_to_mat6(rot)
		return Pose3dCov(
			self.mean,
			rot6d @ self.cov @ rot6d.T
		)
	
	def log(self, end: 'Pose3dCov') -> 'Twist3dCov':
		pass

class Twist3dCov(CovariantWrapper[Twist3d, Literal[6]]):
	STATE_LEN = 6
	
	def mean_vec(self) -> np.ndarray[float, Literal[6]]:
		return np.array([
			self.mean.dx,
			self.mean.dy,
			self.mean.dz,
			self.mean.rx,
			self.mean.ry,
			self.mean.rz,
		])
	
	def transformBy(self, tf: Transform3d) -> 'Pose3dCov':
		tf_rot = rot3_to_mat(tf.rotation())
		tf_rot6 = rot3_to_mat6(tf.rotation())
		dst_cov = tf_rot6 @ self.cov @ tf_rot6.T

		mean = self.mean_vec()
		mean_lin = mean[:3]
		mean_rot = mean[3:]

		tf_lin = np.array([tf.x, tf.y, tf.z])
		dst_rot = tf_rot @ mean_rot
		dst_lin = tf_rot @ mean_lin + np.cross(tf_lin) #TODO
		return Pose3dCov(
			np.concatenate([dst_lin, dst_rot]),
			dst_cov
		)

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
	STATE_LEN = 3

	@classmethod
	def parse_numpy(cls, mean: LinearAcceleration3d | np.ndarray[float, Literal[3]]) -> Pose3d:
		"Parse numpy array as datatype"
		if isinstance(mean, LinearAcceleration3d):
			return mean
		assert np.shape(mean) == (3,)
		return LinearAcceleration3d(
			mean[0],
			mean[1],
			mean[2],
		)
	
	def mean_vec(self) -> np.ndarray[float, Literal[3]]:
		return np.array([
			self.mean.x,
			self.mean.y,
			self.mean.z,
		])

class Acceleration3d:
	linear: LinearAcceleration3d
	angular: AngularAcceleration3d

	def __init__(self, linear: LinearAcceleration3d | None = None, angular: AngularAcceleration3d | None = None):
		self.linear = linear or LinearAcceleration3d()
		self.angular = angular or AngularAcceleration3d()

class Acceleration3dCov(CovariantWrapper[Acceleration3d, Literal[6]]):
	STATE_LEN = 6

	@classmethod
	def parse_numpy(cls, mean: Acceleration3d | np.ndarray[float, Literal[6]]) -> Pose3d:
		"Parse numpy array as datatype"
		if isinstance(mean, LinearAcceleration3d):
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
	
	def mean_vec(self) -> np.ndarray[float, Literal[3]]:
		return np.array([
			self.mean.linear.x,
			self.mean.linear.y,
			self.mean.linear.z,
			self.mean.angular.ax,
			self.mean.angular.ay,
			self.mean.angular.az,
		])


@dataclass
class Odometry:
	stamp: Timestamp
	pose: Pose3dCov
	twist: Twist3dCov

	def isfinite(self):
		return self.pose.isfinite() and self.twist.isfinite()