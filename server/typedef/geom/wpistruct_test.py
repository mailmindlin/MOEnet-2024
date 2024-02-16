from typing import Type, TypeVar
from unittest import TestCase, SkipTest

from .testutil import make_rand
from . import impl as geom

T = TypeVar('T')

class TestStruct(TestCase):
    "Test that we can serialize data types to struct"
    def setUp(self) -> None:
        self.rng = make_rand()
        return super().setUp()
    
    def check_struct(self, type: Type[T]):
        t0 = self.rng(type)
        if not getattr(type, '_WPIStruct', None):
            raise SkipTest()

        ser = type._WPIStruct.pack(t0)
        t1 = type._WPIStruct.unpack(ser)

        assert t0 == t1
    
    def test_Rotation2d(self):
        self.check_struct(geom.Rotation2d)
        
    def test_Translation2d(self):
        self.check_struct(geom.Translation2d)

    def test_Transform2d(self):
        self.check_struct(geom.Transform2d)

    def test_Pose2d(self):
        self.check_struct(geom.Pose2d)

    def test_Twist2d(self):
        self.check_struct(geom.Twist2d)

    def test_Quaternion(self):
        self.check_struct(geom.Quaternion)

    def test_Rotation3d(self):
        self.check_struct(geom.Rotation3d)

    def test_Translation3d(self):
        self.check_struct(geom.Translation3d)

    def test_Transform3d(self):
        self.check_struct(geom.Transform3d)

    def test_Pose3d(self):
        self.check_struct(geom.Pose3d)

    def test_Twist3d(self):
        self.check_struct(geom.Twist3d)