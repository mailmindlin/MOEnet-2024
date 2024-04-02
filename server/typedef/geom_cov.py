from typing import overload, TypeVar, Generic, Literal, ClassVar, Self, Type, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pydantic import PositiveInt

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

def rot2_to_mat(rotation: Rotation2d) -> np.ndarray[tuple[Literal[2], Literal[2]], np.dtype[np.float64]]:
	"Rotation2d into rotation matrix"
	c = rotation.cos()
	s = rotation.sin()
	return np.array([
		[c, s],
		[-s, c],
	], dtype=np.float64)

def rot3_to_mat(rotation: Rotation3d) -> np.ndarray[tuple[Literal[3], Literal[3]], np.dtype[np.floating]]:
	"Rotation3d into rotation matrix"
	q = rotation.getQuaternion()
	i = q.X()
	j = q.Y()
	k = q.Z()
	w = q.W()

	# create rotation matrix
	r = Rotation.from_quat([i, j, k, w])
	return r.as_matrix()

def rot3_to_mat6(rotation: Rotation3d) -> np.ndarray[tuple[Literal[6], Literal[6]], np.dtype[np.floating]]:
	"Make 6d-rotation matrix"
	rmat = rot3_to_mat(rotation)
	rot6d = np.eye(6, 6, dtype=np.floating)
	rot6d[:3,:3] = rmat
	rot6d[3:,3:] = rmat
	return rot6d

def rot3_flatten(rotation: Rotation3d) -> Rotation3d:
	"Flatten to the x-y plane (only preserve yaw)"
	yaw = rotation.Z()
	return Rotation3d(0, 0, yaw)


T = TypeVar('T')
N = TypeVar('N', bound=int)

class Covariant(ABC, Generic[N]):
	"Abstract base type for data with mean and covariance matrix"
	STATE_LEN: ClassVar[int] = 0

	cov: np.ndarray[tuple[N, N], np.dtype[np.floating]]
	"Covariance matrix"

	def __init__(self, cov: np.ndarray[tuple[N, N], np.dtype[np.floating]] | None = None) -> None:
		super().__init__()
		if cov is None:
			cov = np.zeros((self.STATE_LEN, self.STATE_LEN), dtype=float)
		else:
			cov = np.asanyarray(cov)
		assert np.shape(cov) == (self.STATE_LEN, self.STATE_LEN)
		self.cov = cov
	
	def isfinite(self) -> bool:
		"Are the mean and covariance matrix elements all finite?"
		return bool(np.all(np.isfinite(self.mean_vec())) and np.all(np.isfinite(self.cov)))
	
	@abstractmethod
	def mean_vec(self) -> np.ndarray[tuple[N], np.dtype[np.floating]]:
		"Get mean, as numpy array"
		pass


class CovariantWrapper(Covariant[N], Generic[T, N]):
	"Wrapper to help add covariance matrix to a type"
	@classmethod
	def parse_numpy(cls, mean: T | np.ndarray[tuple[N], np.dtype[np.floating]]) -> T:
		"Parse numpy array as datatype"
		return mean
	
	def __init__(self, mean: T | np.ndarray[tuple[N], np.dtype[np.floating]], cov: np.ndarray[tuple[N, N], np.dtype[np.floating]] | None = None):
		super().__init__(cov)
		self.mean = type(self).parse_numpy(mean)
	
	def __iter__(self):
		return self
	
	def __next__(self):
		return self.sample()
	
	@overload
	def sample(self) -> T:
		"Sample a single possible value from this distribution"
	@overload
	def sample(self, n: PositiveInt) -> list[T]:
		"Sample multiple values from this distribution"
	def sample(self, n: PositiveInt | None = None):
		mean_np = self.mean_vec()
		assert (n is None) or (n > 0)

		sample = np.random.multivariate_normal(mean_np, self.cov, n)

		# We need to help out the type checker a bit
		def parse_numpy(v: np.ndarray[tuple[N], np.dtype[np.floating]]) -> T:
			return type(self).parse_numpy(v)
		
		if n is None:
			return parse_numpy(sample)
		else:
			return [
				parse_numpy(sample[i])
				for i in range(n)
			]
	
	# def __matmul__(self, tf: np.ndarray[tuple[N], np.dtype[np.floating]]):
	# 	pass

class LinearCovariantBase(CovariantWrapper[T, N]):
	"CovariantWrapper with some extra methods assuming T is linear"
	@classmethod
	def _try_wrap(cls, other: T | Self | np.ndarray[tuple[N], np.dtype[np.floating]]) -> Self:
		if isinstance(other, cls):
			return other
		try:
			other = cls.parse_numpy(other)
		except:
			return NotImplemented
		assert isinstance(other, cls)
		return other
	
	def __neg__(self) -> Self:
		return type(self)(-self.mean_vec(), self.cov)
	
	def __pos__(self):
		return self

	def __add__(self, other: T | Self | np.ndarray[tuple[N], np.dtype[np.floating]]) -> Self:
		cls = type(self)
		other = cls._try_wrap(other)
		if isinstance(other, cls):
			return cls(self.mean_vec() + other.mean_vec(), self.cov + other.cov)
		return NotImplemented
	
	__radd__ = __add__
	
	def __sub__(self, other: T | Self | np.ndarray[tuple[N], np.dtype[np.floating]]) -> Self:
		cls = type(self)
		other = cls._try_wrap(other)
		if isinstance(other, cls):
			return cls(self.mean_vec() - other.mean_vec(), self.cov + other.cov)
		return NotImplemented
	
	def __rsub__(self, other: T | Self | np.ndarray[tuple[N], np.dtype[np.floating]]) -> Self:
		cls = type(self)
		other = cls._try_wrap(other)
		if isinstance(other, cls):
			return cls(other.mean_vec() - self.mean_vec(), self.cov + other.cov)
		return NotImplemented

	

class RandomNormal(LinearCovariantBase[float, Literal[1]]):
	"Random normal variable"
	STATE_LEN: ClassVar[int] = 1

	@classmethod
	def wrap(cls: Type[Self], value: float | Self) -> Self:
		if isinstance(value, cls):
			return value
		else:
			return cls(float(value))

	@classmethod
	def parse_numpy(cls, mean: float | np.ndarray[tuple[Literal[1]], np.dtype[np.floating]]) -> float:
		arr = np.asanyarray(mean, dtype=np.float64)
		assert np.shape(arr) == (1,)
		return arr.item(0)
	
	def __float__(self):
		return self.mean

	def __mul__(self, scalar: float) -> 'RandomNormal':
		if isinstance(scalar, np.floating):
			return RandomNormal(self.mean * scalar, np.square(scalar) * self.cov)
		return NotImplemented
	__rmul__ = __mul__

	def __div__(self, scalar: float) -> 'RandomNormal':
		if isinstance(scalar, np.floating):
			return self * np.reciprocal(scalar)
		return NotImplemented
	
	def mean_vec(self) -> ndarray[tuple[Literal[1]], np.dtype[np.float64]]:
		return np.array([self.mean], dtype=np.float64)


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

class Translation3dCov(LinearCovariantBase[Translation3d, Literal[3]]):
	STATE_LEN: ClassVar[int] = 3
	def rotateBy(self, rotation: Rotation3d) -> 'Translation3dCov':
		mean = self.mean.rotateBy(rotation)
		rot = rot3_to_mat(rotation)
		cov = rot @ self.cov @ rot.T
		return Translation3dCov(mean, cov)
	
	def toTranslation2d(self) -> Translation2dCov:
		return Translation2dCov(
			self.mean.toTranslation2d(),
			self.cov[:2, :2],
		)

	def mean_vec(self) -> np.ndarray[tuple[Literal[3]], np.dtype[np.float64]]:
		return np.asanyarray(self.mean.toVector(), dtype=np.float64)

class Pose3dQuatCov(CovariantWrapper[Pose3d, Literal[7]]):
	STATE_LEN: ClassVar[int] = 7
	
	@classmethod
	def parse_numpy(cls, mean: Pose3d | np.ndarray[tuple[Literal[7]], np.dtype[np.floating]]) -> Pose3d:
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

	def mean_vec(self) -> ndarray[tuple[Literal[7]], np.dtype[np.floating]]:
		quat = self.mean.rotation().getQuaternion()
		return np.array([
			self.mean.x,
			self.mean.y,
			self.mean.z,
			quat.X(),
			quat.Y(),
			quat.Z(),
			quat.W(),
		], dtype=np.float64)

class Pose3dCov(CovariantWrapper[Pose3d, Literal[6]]):
	STATE_LEN: ClassVar[int] = 6
	@classmethod
	def parse_numpy(cls, mean: Pose3d | np.ndarray[tuple[Literal[6]], np.dtype[np.floating]]) -> Pose3d:
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
	
	def mean_vec(self) -> np.ndarray[tuple[Literal[6]], np.dtype[np.float64]]:
		rot = self.mean.rotation()
		return np.array([
			self.mean.x,
			self.mean.y,
			self.mean.z,
			rot.X(),
			rot.Y(),
			rot.Z(),
		], dtype=np.float64)

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
	STATE_LEN: ClassVar[int] = 6
	
	def mean_vec(self) -> np.ndarray[tuple[Literal[6]], np.dtype[np.float64]]:
		return np.array([
			self.mean.dx,
			self.mean.dy,
			self.mean.dz,
			self.mean.rx,
			self.mean.ry,
			self.mean.rz,
		], dtype=np.float64)
	
	def transformBy(self, tf: Transform3d) -> 'Pose3dCov':
		tf_rot = rot3_to_mat(tf.rotation())
		tf_rot6 = rot3_to_mat6(tf.rotation())
		dst_cov = tf_rot6 @ self.cov @ tf_rot6.T

		mean = self.mean_vec()
		mean_lin = mean[:3]
		mean_rot = mean[3:]

		tf_lin = np.array([tf.x, tf.y, tf.z], dtype=mean.dtype)
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


@dataclass
class Odometry:
	stamp: Timestamp
	pose: Pose3dCov
	twist: Twist3dCov

	def isfinite(self):
		return self.pose.isfinite() and self.twist.isfinite()