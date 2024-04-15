from typing import Type, TypeVar
from unittest import TestCase, SkipTest

from wpiutil.wpistruct import StructDescriptor
from .testutil import make_rand
from . import impl as geom

class TestStruct(TestCase):
    "Test that we can serialize data types to struct"
    def setUp(self) -> None:
        self.rng = make_rand()
        return super().setUp()
    
    def check_struct[T](self, type: type[T]):
        t0 = self.rng(type)
        ws: StructDescriptor | None = getattr(type, '_WPIStruct', None)
        if not ws:
            raise SkipTest("wpistruct not implemented")

        ser = ws.pack(t0)
        t1 = ws.unpack(ser)

        self.assertEqual(t0, t1)
    
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