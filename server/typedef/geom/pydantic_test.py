from typing import Type, TypeVar
from unittest import TestCase

from pydantic import BaseModel

from .testutil import make_rand
from . import impl as geom

T = TypeVar('T')

class TestJson(TestCase):
    "Test that we can serialize data types to JSON (useful for network)"
    def setUp(self) -> None:
        self.rng = make_rand()
        return super().setUp()
    
    def check_json(self, type: Type[T]):
        # Wrap datatype in Pydantic model to make life easier
        #TODO: should this be RootModel?
        class Model(BaseModel):
            value: type
        
        t0 = self.rng(type)
        m0 = Model(value=t0)
        ser = m0.model_dump_json()
        m1 = Model.model_validate_json(ser)
        t1 = m1.value
        self.assertEqual(t0, t1)
    
    def test_Rotation2d(self):
        self.check_json(geom.Rotation2d)
        
    def test_Translation2d(self):
        self.check_json(geom.Translation2d)

    def test_Transform2d(self):
        self.check_json(geom.Transform2d)

    def test_Pose2d(self):
        self.check_json(geom.Pose2d)

    def test_Twist2d(self):
        self.check_json(geom.Twist2d)

    def test_Quaternion(self):
        self.check_json(geom.Quaternion)

    def test_Rotation3d(self):
        self.check_json(geom.Rotation3d)

    def test_Translation3d(self):
        self.check_json(geom.Translation3d)

    def test_Transform3d(self):
        self.check_json(geom.Transform3d)

    def test_Pose3d(self):
        self.check_json(geom.Pose3d)

    def test_Twist3d(self):
        self.check_json(geom.Twist3d)