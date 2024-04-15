from unittest import TestCase

from wpimath.geometry import Pose3d, Rotation3d, Translation3d, Transform3d
import numpy as np
import numpy.testing as npt

from .se3 import Pose3dCov

def make_cov(**kwargs) -> np.ndarray:
	res = np.zeros((6,6), dtype=float)
	idxs = ['x', 'y', 'z', 'X', 'Y', 'Z'] # Rotation is capitalized
	for key, value in kwargs.items():
		if '_' in key:
			a, b = key.split('_')
		else:
			a = b = key
		a = idxs.index(a)
		b = idxs.index(b)
		res[a, b] = value
		res[b, a] = value
	return res

class TestPose3dCov(TestCase):
	def test_construct(self):
		pose = Pose3dCov(Pose3d())
		self.assertEqual(pose.mean, Pose3d())
		npt.assert_array_equal(pose.cov, np.zeros((6,6)))
	
	def test_make_cov(self):
		cov = np.zeros((6,6), dtype=float)
		cov[0,0] = 1.0
		cov[1,1] = 2.0
		cov[2,0] = cov[0,2] = 3.0
		npt.assert_array_equal(cov, make_cov(x=1.0,y=2.0, x_z=3.0))
	
	def test_translate(self):
		cov = make_cov(x=1, y=2)
		poseA = Pose3dCov(Pose3d(Translation3d(3,2,1), Rotation3d()), cov)
		poseB = poseA.transformBy(Transform3d(Translation3d(1,0,0), Rotation3d()))
		self.assertEqual(poseA.rotation, poseB.rotation)
		self.assertEqual(poseB.translation.mean, Translation3d(4,2,1))
		npt.assert_array_almost_equal(poseB.cov, cov)

	def test_rotate(self):
		cov = make_cov(x=1, y=2)
		poseA = Pose3dCov(Pose3d(Translation3d(3,2,1), Rotation3d()), cov)
		poseB = poseA.transformBy(Transform3d(Translation3d(), Rotation3d.fromDegrees(0,0,90)))
		self.assertEqual(poseB.rotation, Rotation3d.fromDegrees(0,0,90))
		self.assertEqual(poseB.translation.mean, Translation3d(3, 2, 1))
		npt.assert_array_almost_equal(poseB.cov, make_cov(x=2, y=1))
	
	def test_transform(self):
		cov = make_cov(x=1, y=2)
		poseA = Pose3dCov(Pose3d(Translation3d(3,2,1), Rotation3d()), cov)
		poseB = poseA.transformBy(Transform3d(Translation3d(1,0,0), Rotation3d.fromDegrees(0,0,90)))
		self.assertEqual(poseB.rotation, Rotation3d.fromDegrees(0,0,90))
		self.assertEqual(poseB.translation.mean, Translation3d(4, 2, 1)) # Translation shifted 1 => +x
		npt.assert_array_almost_equal(poseB.cov, make_cov(x=2, y=1))
		