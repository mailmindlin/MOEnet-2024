from typing import overload, TypeVar, Generic, Literal, ClassVar, Self, Type, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pydantic import PositiveInt

import numpy as np
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


def mahalanobisDistance2(mean_diff: np.ndarray[tuple[N], np.dtype[np.floating]], cov_sum: np.ndarray[tuple[N, N], np.dtype[np.floating]]) -> float:
	"Squared mahalanobis distance"
	cov_inv = np.linalg.inv(cov_sum)
	return (cov_inv.T @ mean_diff @ cov_inv).item(0)

def mahalanobisDistance(mean_diff: np.ndarray[tuple[N], np.dtype[np.floating]], cov_sum: np.ndarray[tuple[N, N], np.dtype[np.floating]]) -> float:
	return np.sqrt(mahalanobisDistance2(mean_diff, cov_sum))
	

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
	
	def __repr__(self):
		return f'{type(self).__name__}(mean={self.mean!r}, cov={self.cov})'
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
	
	def mean_vec(self) -> np.ndarray[tuple[Literal[1]], np.dtype[np.float64]]:
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

class Translation3dCov(LinearCovariantBase[Translation3d, Literal[3]]):
	STATE_LEN: ClassVar[int] = 3

	def mean_vec(self) -> np.ndarray[tuple[Literal[3]], np.dtype[np.float64]]:
		return np.asanyarray(self.mean.toVector(), dtype=np.float64)
	
	@property
	def x(self) -> RandomNormal:
		return RandomNormal(self.mean.x, self.cov[0,0])
	
	@property
	def y(self) -> RandomNormal:
		return RandomNormal(self.mean.y, self.cov[1,1])
	
	@property
	def z(self) -> RandomNormal:
		return RandomNormal(self.mean.y, self.cov[2,2])
	
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
	
	def mahalanobisDistanceTo(self, other: Self | Translation3d, only2d: bool = False) -> float:
		"Returns the Mahalanobis distance from this PDF to some other point"
		if isinstance(other, Translation3d):
			mean2 = other
			cov2 = np.zeros_like(self.cov)
		else:
			mean2 = other.mean
			cov2 = other.cov
		
		# Difference in means
		deltaX = (mean2 - self.mean).toVector()
		cov = self.cov + cov2
		
		if only2d:
			cov = cov[:2,:2]
			deltaX = deltaX[:2]
		
		cov_inv = np.linalg.inv(cov)
		return np.sqrt(deltaX.T @ cov_inv @ deltaX)

def quat_normalizationJacobian(quat: Quaternion) -> np.ndarray[tuple[Literal[4], Literal[4]], np.dtype[np.float64]]:
	"""
	Calculate the 4x4 Jacobian of the normalization operation of this
	quaternion.
	
	The output matrix can be a dynamic or fixed size (4x4) matrix.
	"""
	n = 1.0 / np.power(quat.norm(), 1.5 * 2)
	J = np.empty((4, 4), dtype=float)
	x = quat.X()
	y = quat.Y()
	z = quat.Z()
	r = quat.W()
	
	J[0, 0] = x * x + y * y + z * z
	J[0, 1] = -r * x
	J[0, 2] = -r * y
	J[0, 3] = -r * z

	J[1, 0] = -x * r
	J[1, 1] = r * r + y * y + z * z
	J[1, 2] = -x * y
	J[1, 3] = -x * z

	J[2, 0] = -y * r
	J[2, 1] = -y * x
	J[2, 2] = r * r + x * x + z * z
	J[2, 3] = -y * z

	J[3, 0] = -z * r
	J[3, 1] = -z * x
	J[3, 2] = -z * y
	J[3, 3] = r * r + x * x + y * y
	J *= n
	return J

def quat_rotationJacobian(quat: Quaternion) -> np.ndarray[tuple[Literal[4], Literal[4]], np.dtype[np.float64]]:
	"""
	Compute the Jacobian of the rotation composition operation \f$ p =
	f(\cdot) = q_{this} \times r \f$, that is the 4x4 matrix \f$
	\frac{\partial f}{\partial q_{this} }  \f$.
	The output matrix can be a dynamic or fixed size (4x4) matrix.
	"""
	x = quat.X()
	y = quat.Y()
	z = quat.Z()
	r = quat.W()
	return np.array([
		[r, -x, -y, -z],
		[x, r, -z, y],
		[y, z, r, -x],
		[z, -y, x, r],
	], dtype=np.float64)

def quat_inverseRotatePoint(this: Quaternion, l: Translation3d) -> Translation3d:
	"""
	Rotate a 3D point (lx,ly,lz) -> (gx,gy,gz) as described by the inverse
	(conjugate) of this quaternion
	"""
	r = this.W()
	x = this.X()
	y = this.Y()
	z = this.Z()
	t2 = -r * x
	t3 = -r * y
	t4 = -r * z
	t5 = -x * x
	t6 = x * y
	t7 = x * z
	t8 = -y * y
	t9 = y * z
	t10 = -z * z
	lx = l.x
	ly = l.y
	lz = l.z
	gx = 2 * ((t8 + t10) * lx + (t6 - t4) * ly + (t3 + t7) * lz) + lx
	gy = 2 * ((t4 + t6) * lx + (t5 + t10) * ly + (t9 - t2) * lz) + ly
	gz = 2 * ((t7 - t3) * lx + (t2 + t9) * ly + (t5 + t8) * lz) + lz
	return Translation3d(gx, gy, gz)

def pose3_inverseComposePoint(this: Pose3d, g: Translation3d, out_jacobian_df_dpoint: bool = False, out_jacobian_df_dpose: bool = False):
	"""
	Computes the 3D point G such as \f$ L = G \ominus this \f$.
 	\sa composeFrom
	 """
	m_quat = this.rotation().getQuaternion()
	m_quat_x = m_quat.X()
	m_quat_y = m_quat.Y()
	m_quat_z = m_quat.Z()
	m_quat_r = m_quat.W()
	
	jacobian_df_dpoint = None
	jacobian_df_dpose = None
	
	if (out_jacobian_df_dpoint or out_jacobian_df_dpose):
		qx2 = np.square(m_quat.X())
		qy2 = np.square(m_quat.Y())
		qz2 = np.square(m_quat.Z())

		# Jacob: df/dpoint
		if out_jacobian_df_dpoint:
			# 3x3:  df_{m_quat_r} / da
			#		inv_df_da =
			#		[ - 2*qy^2 - 2*qz^2 + 1,     2*qx*qy - 2*qr*qz,     2*qr*qy
			#+
			# 2*qx*qz]
			#		[     2*qr*qz + 2*qx*qy, - 2*qx^2 - 2*qz^2 + 1,     2*qy*qz
			#-
			# 2*qr*qx]
			#		[     2*qx*qz - 2*qr*qy,     2*qr*qx + 2*qy*qz, - 2*qx^2 -
			# 2*qy^2 + 1]
			#

			jacobian_df_dpoint = np.array([
				[
					1 - 2 * (qy2 + qz2),
					2 * (m_quat_x * m_quat_y + m_quat_r * m_quat_z),
					2 * (-m_quat_r * m_quat_y + m_quat_x * m_quat_z),
				],
				[
					2 * (-m_quat_r * m_quat_z + m_quat_x * m_quat_y),
					1 - 2 * (qx2 + qz2),
					2 * (m_quat_y * m_quat_z + m_quat_r * m_quat_x),
				],
				[
					2 * (m_quat_x * m_quat_z + m_quat_r * m_quat_y),
					2 * (-m_quat_r * m_quat_x + m_quat_y * m_quat_z),
					1 - 2 * (qx2 + qy2),
				],
			])
		# Jacob: df/dpose
		if (out_jacobian_df_dpose):
			# 3x7:  df_{m_quat_r} / dp
			#		inv_df_dp =
			#[ 2*qy^2 + 2*qz^2 - 1, - 2*qr*qz - 2*qx*qy,   2*qr*qy - 2*qx*qz,
			# 2*qz*(ay - y) - 2*qy*(az - z),                 2*qy*(ay - y) +
			# 2*qz*(az - z), 2*qx*(ay - y) - 4*qy*(ax - x) - 2*qr*(az - z),
			# 2*qr*(ay - y) - 4*qz*(ax - x) + 2*qx*(az - z)]
			#[   2*qr*qz - 2*qx*qy, 2*qx^2 + 2*qz^2 - 1, - 2*qr*qx - 2*qy*qz,
			# 2*qx*(az - z) - 2*qz*(ax - x), 2*qy*(ax - x) - 4*qx*(ay - y) +
			# 2*qr*(az - z),                 2*qx*(ax - x) + 2*qz*(az - z),
			# 2*qy*(az - z) - 4*qz*(ay - y) - 2*qr*(ax - x)]
			#[ - 2*qr*qy - 2*qx*qz,   2*qr*qx - 2*qy*qz, 2*qx^2 + 2*qy^2 - 1,
			# 2*qy*(ax - x) - 2*qx*(ay - y), 2*qz*(ax - x) - 2*qr*(ay - y) -
			# 4*qx*(az - z), 2*qr*(ax - x) + 2*qz*(ay - y) - 4*qy*(az - z),
			# 2*qx*(ax - x) + 2*qy*(ay - y)]
			
			qr = m_quat.W()
			qx = m_quat.X()
			qy = m_quat.Y()
			qz = m_quat.Z()

			jacobian_df_dpose = np.array([
				[
					2 * qy2 + 2 * qz2 - 1,
					-2 * qr * qz - 2 * qx * qy,
					2 * qr * qy - 2 * qx * qz,
					0,
					0,
					0,
					0,
				],
				[
					2 * qr * qz - 2 * qx * qy,
					2 * qx2 + 2 * qz2 - 1,
					-2 * qr * qx - 2 * qy * qz,
					0,
					0,
					0,
					0,
				],
				[
					-2 * qr * qy - 2 * qx * qz,
					2 * qr * qx - 2 * qy * qz,
					2 * qx2 + 2 * qy2 - 1,
					0,
					0,
					0,
					0,
				],
			])

			A = 2 * (g - this.translation()).toVector()
			Ax = A[0]
			Ay = A[1]
			Az = A[2]

			vals = np.array([
				[
					-qy * Az + qz * Ay,
					qy * Ay + qz * Az,
					qx * Ay - 2 * qy * Ax - qr * Az,
					qx * Az + qr * Ay - 2 * qz * Ax,
				],
				[
					qx * Az - qz * Ax,
					qy * Ax - 2 * qx * Ay + qr * Az,
					qx * Ax + qz * Az,
					qy * Az - 2 * qz * Ay - qr * Ax,
				],
				[
					qy * Ax - qx * Ay,
					qz * Ax - qr * Ay - 2 * qx * Az,
					qr * Ax + qz * Ay - 2 * qy * Az,
					qx * Ax + qy * Ay
				],
			])
			
			norm_jacob = quat_normalizationJacobian(m_quat)
			jacobian_df_dpose[:, 3:] = vals @ norm_jacob

	# function itself:
	trl = this.translation()
	l = quat_inverseRotatePoint(m_quat, g - trl)
	return l, jacobian_df_dpoint, jacobian_df_dpose
	
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

	def mean_vec(self) -> np.ndarray[tuple[Literal[7]], np.dtype[np.floating]]:
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