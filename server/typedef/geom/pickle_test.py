from typing import Type, TypeVar
from unittest import TestCase

from .testutil import make_rand
from . import impl as geom

T = TypeVar('T')


class TestPickle(TestCase):
    "Test that we can serialize data types to pickle (useful for multiprocessing messages)"
    def setUp(self) -> None:
        self.rng = make_rand()
        return super().setUp()
    
    def check_pickle(self, type: Type[T]):
        import pickle
        t0 = self.rng(type)
        ser = pickle.dumps(t0)
        t1 = pickle.loads(ser)
        self.assertEqual(t0, t1)
    
    def test_Rotation2d(self):
        self.check_pickle(geom.Rotation2d)
        
    def test_Translation2d(self):
        self.check_pickle(geom.Translation2d)

    def test_Transform2d(self):
        self.check_pickle(geom.Transform2d)

    def test_Pose2d(self):
        self.check_pickle(geom.Pose2d)

    def test_Twist2d(self):
        self.check_pickle(geom.Twist2d)

    def test_Quaternion(self):
        self.check_pickle(geom.Quaternion)

    def test_Rotation3d(self):
        self.check_pickle(geom.Rotation3d)

    def test_Translation3d(self):
        self.check_pickle(geom.Translation3d)

    def test_Transform3d(self):
        self.check_pickle(geom.Transform3d)

    def test_Pose3d(self):
        self.check_pickle(geom.Pose3d)

    def test_Twist3d(self):
        self.check_pickle(geom.Twist3d)