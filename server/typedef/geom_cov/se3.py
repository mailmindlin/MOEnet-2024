from typing import Literal, ClassVar, Self, Union

import numpy as np
from scipy.spatial.transform import Rotation

from .base import LinearCovariantBase, CovariantWrapper, mahalanobisDistance
from .multi import RandomNormal
from .se2 import Translation2dCov
from ..geom import Rotation3d, Translation3d, Pose3d, Quaternion, Transform3d, Twist3d

def rot3_to_mat(rotation: Rotation3d) -> np.ndarray[tuple[Literal[3], Literal[3]], np.dtype[np.floating]]:
	"Rotation3d into 3x3 rotation matrix"
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
	rot6d = np.zeros((6, 6), dtype=np.floating)
	rot6d[:3,:3] = rmat
	rot6d[3:,3:] = rmat
	return rot6d

def rot3_flatten(rotation: Rotation3d) -> Rotation3d:
	"Flatten to the x-y plane (only preserve yaw)"
	yaw = rotation.Z()
	return Rotation3d(0, 0, yaw)

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
	
	@property
	def rotation(self):
		return self.mean.rotation()
	
	@property
	def translation(self):
		return self.mean.translation()
	
	@staticmethod
	def jacobiansPoseComposition(x: Pose3d, u: Pose3d | Transform3d):
		x_quat = x.rotation().getQuaternion()
		qr = x_quat.W()
		qx = x_quat.X()
		qx2 = np.square(qx)
		qy = x_quat.Y()
		qy2 = np.square(qy)
		qz = x_quat.Z()
		qz2 = np.square(qz)

		u_trl = u.translation()
		ax = u_trl.x
		ay = u_trl.y
		az = u_trl.z
		u_quat = u.rotation().getQuaternion()
		q2r = u_quat.W()
		q2x = u_quat.X()
		q2y = u_quat.Y()
		q2z = u_quat.Z()

		x_plus_u = x + Transform3d(u.translation(), u.rotation());	 # for the normalization Jacobian
		norm_jacob = quat_normalizationJacobian(x_plus_u.rotation().getQuaternion())

		norm_jacob_x = quat_normalizationJacobian(x_quat)

		# df_dx ===================================================
		df_dx = np.zeros((7, 7), dtype=np.float64)

		# first part 3x7:  df_{qr} / dp
		df_dx[:3, :3] = np.eye(3)

		vals2 = np.array([
			[
				(-qz * ay + qy * az),
				(qy * ay + qz * az),
				(-2 * qy * ax + qx * ay + qr * az),
				(-2 * qz * ax - qr * ay + qx * az),
			],
			[
				(qz * ax - qx * az),
				(qy * ax - 2 * qx * ay - qr * az),
				(qx * ax + qz * az),
				(qr * ax - 2 * qz * ay + qy * az),
			],
			[
				(-qy * ax + qx * ay),
				(qz * ax + qr * ay - 2 * qx * az),
				(-qr * ax + qz * ay - 2 * qy * az),
				(qx * ax + qy * ay),
			]
		])
		vals2 *= 2.0
		df_dx[0:3, 3:7] = vals2 @ norm_jacob_x
		
		# second part:
		aux44_data = np.array([
			[q2r, -q2x, -q2y, -q2z],
			[q2x, q2r, q2z,  -q2y],
			[q2y, -q2z, q2r, q2x],
			[q2z, q2y, -q2x, q2r],
		])
		df_dx[3:7,3:7] = norm_jacob @ aux44_data

		# df_du ===================================================
		df_du = np.zeros((7, 7), dtype=np.float64)

		# first part 3x3:  df_{qr} / da
		df_du[0, 0] = 1 - 2 * (qy2 + qz2)
		df_du[0, 1] = 2 * (qx * qy - qr * qz)
		df_du[0, 2] = 2 * (qr * qy + qx * qz)

		df_du[1, 0] = 2 * (qr * qz + qx * qy)
		df_du[1, 1] = 1 - 2 * (qx2 + qz2)
		df_du[1, 2] = 2 * (qy * qz - qr * qx)

		df_du[2, 0] = 2 * (qx * qz - qr * qy)
		df_du[2, 1] = 2 * (qr * qx + qy * qz)
		df_du[2, 2] = 1 - 2 * (qx2 + qy2)

		# Second part:
		aux44_data = np.array([
			[qr, -qx, -qy, -qz],
			[qx, qr,	-qz, qy],
			[qy, qz,	 qr,  -qx],
			[qz, -qy, qx,	 qr]
		])
		df_du[3:7,3:7] = norm_jacob @ aux44_data

		return (df_dx, df_du, x_plus_u)
	
	def __add__(self, other: Self | Pose3d | Transform3d) -> 'Pose3dQuatCov':
		if isinstance(other, (Pose3d, Transform3d)):
			df_dx, df_du, mean = self.jacobiansPoseComposition(self.mean, other)
			# cov = H1*this->cov*H1' + H2*Ap.cov*H2'
			cov = df_dx @ self.cov @ df_dx.T
			return Pose3dQuatCov(
				mean,
				cov
			)
		elif isinstance(other, Pose3dQuatCov):
			df_dx, df_du, mean = self.jacobiansPoseComposition(self.mean, other.mean)
			# cov = H1*this->cov*H1' + H2*Ap.cov*H2'
			cov = df_dx @ self.cov @ df_dx.T
			cov += df_du @ other.cov @ df_du.T
			return Pose3dQuatCov(
				mean,
				cov
			)
		return NotImplemented
	
	def __sub__(self, other: 'Pose3dQuatCov | Pose3d | Transform3d') -> 'Pose3dQuatCov':
		if isinstance(other, Pose3d):
			other = Transform3d(other.translation(), other.rotation())
		if isinstance(other, Transform3d):
			return self + other.inverse()
		elif isinstance(other, Pose3dQuatCov):
			return self + other.inverse()
		return NotImplemented
	
	def mahalanobisDistanceTo(self, other: 'Pose3dQuatCov') -> float:
		cov = self.cov + other.cov
		return mahalanobisDistance(self.mean_vec() - other.mean_vec(), cov)
	
	def inverseJacobian(self) -> np.ndarray[tuple[Literal[7], Literal[7]], np.dtype[np.floating]]:
		l, _, jacobian_df_pose = pose3_inverseComposePoint(self.mean, Translation3d(), out_jacobian_df_dpose=True)
		assert jacobian_df_pose is not None
		jacob = np.zeros((7, 7), dtype=float)
		jacob[:3, :] = jacobian_df_pose
		jacob[3, 3] = 1
		jacob[4, 4] = -1
		jacob[5, 5] = -1
		jacob[6, 6] = -1
		norm_jacob = quat_normalizationJacobian(self.mean.rotation().getQuaternion())
		jacob[3:,3:] *= norm_jacob #TODO: I can't tell if this is supposed to be element-wise or a matmul
		return jacob
	
	def inverse(self) -> 'Pose3dQuatCov':
		# https://github.com/MRPT/mrpt/blob/4c9da0fb51e50148d28c46964bd698688c727f47/libs/poses/src/CPose3DQuatPDFGaussian.cpp#L281
		#TODO: Just use wpilib inverse
		l, _, _ = pose3_inverseComposePoint(self.mean, Translation3d())
		
		jacob = self.inverseJacobian()

		# C(0:2,0:2): H C H^t
		cov = jacob @ self.cov @ jacob.T

		# Mean:
		mean = Pose3d(
			l,
			-self.mean.rotation(),
		)
		
		return Pose3dQuatCov(mean, cov)
	
	__neg__ = inverse
	
	def changeCoordinatesReference(self, newReferenceBase: Pose3d) -> 'Pose3dQuatCov':
		df_dx, df_du, mean = self.jacobiansPoseComposition(newReferenceBase, self.mean)
		cov = df_du @ self.cov @ df_du.T
		return Pose3dQuatCov(mean, cov)
	
	
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
		"Get mean rotation"
		return self.mean.rotation()
	
	@property
	def translation(self):
		"Get translation"
		return Translation3dCov(
			mean=self.mean.translation(),
			cov=self.cov[:3, :3],
		)
	
	def inverse(self) -> 'Pose3dCov':
		"Inverse pose"
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

	def relativeTo(self, other: Pose3d) -> Self:
		tf = Transform3d(other, self.mean)
		return self.transformBy(tf)
	
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

class Transform3dCov(CovariantWrapper[Transform3d, Literal[6]]):
	STATE_LEN: ClassVar[int] = 6
	@classmethod
	def parse_numpy(cls, mean: Transform3d | np.ndarray[tuple[Literal[6]], np.dtype[np.floating]]) -> Transform3d:
		"Parse numpy array as datatype"
		if isinstance(mean, Transform3d):
			return mean
		assert np.shape(mean) == (6,)
		return Transform3d(
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
		"Get mean rotation"
		return self.mean.rotation()
	
	@property
	def translation(self):
		"Get translation"
		return Translation3dCov(
			mean=self.mean.translation(),
			cov=self.cov[:3, :3],
		)
	
	def inverse(self) -> 'Transform3dCov':
		"Inverse pose"
		# This is like: b=(0,0,0)
		#  OUT = b - THIS
		zero = Transform3dCov(Transform3d(), np.zeros_like(self.cov))
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
	
	def __add__(self, tf: Transform3d | Self) -> Self:
		if isinstance(tf, Transform3dCov):
			#TODO
			pass
		elif isinstance(tf, Transform3d):
			rot = rot3_to_mat6(tf.rotation())
			cov_rotated = rot @ self.cov @ rot.T
			return type(self)(self.mean + tf, cov_rotated)
		return NotImplemented


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
