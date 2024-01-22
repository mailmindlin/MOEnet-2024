from typing import TypeVar, Type
from unittest import TestCase, SkipTest
from . import geom
from random import Random
from wpimath.geometry import Twist3d
from wpimath import geometry as geom

T = TypeVar('T')

rand_info = {
    geom.Translation2d: (float, float),
    geom.Transform2d: (geom.Translation2d, geom.Rotation2d),
    geom.Pose2d: (geom.Translation2d, geom.Rotation2d),
    geom.Twist2d: (float, float, float),
    geom.Translation3d: (float, float, float),
    geom.Quaternion: (float, float, float, float),
    geom.Transform3d: (geom.Translation3d, geom.Rotation3d),
    geom.Pose3d: (geom.Translation3d, geom.Rotation3d),
    geom.Twist3d: (float, float, float, float, float, float),
}

def rand_t(t: Type[T], rng: Random) -> T:
    if t == float:
        return rng.random()
    if t == geom.Rotation2d:
        return geom.Rotation2d.fromDegrees(rng.random() * 360)
    if t == geom.Rotation3d:
        return geom.Rotation3d.fromDegrees(rng.random() * 360, rng.random() * 360, rng.random() * 360)
    if t == geom.Quaternion:
        return rand_t(geom.Rotation3d, rng).getQuaternion()
    if info := rand_info.get(t, None):
        args = [
            rand_t(ftype, rng)
            for ftype in info
        ]
        return t(*args)
    raise TypeError('Unable to make type ' + t.__name__)

def make_rand():
    rng = Random()
    def rand_t1(t: Type[T]) -> T:
        return rand_t(t, rng)
    return rand_t1

class TestStruct(TestCase):
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


class TestPickle(TestCase):
    def setUp(self) -> None:
        self.rng = make_rand()
        return super().setUp()
    
    def check_struct(self, type: Type[T]):
        t0 = self.rng(type)

        ser = type._WPIStruct.pack(t0)
        t1 = type._WPIStruct.unpack(ser)

        assert t0 == t1
    
    def check_pickle(self, type: Type[T]):
        import pickle
        t0 = self.rng(type)
        ser = pickle.dumps(t0)
        t1 = pickle.loads(ser)
        assert t0 == t1
    
    def check_json(self, type: Type[T]):
        from pydantic import BaseModel
        class Model(BaseModel):
            value: type
        
        t0 = self.rng(type)
        m0 = Model(value=t0)
        ser = m0.model_dump_json()
        m1 = Model.model_validate_json(ser)
        t1 = m1.value
        assert t0 == t1
    
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


class TestJson(TestCase):
    def setUp(self) -> None:
        self.rng = make_rand()
        return super().setUp()
    
    def check_json(self, type: Type[T]):
        from pydantic import BaseModel
        class Model(BaseModel):
            value: type
        
        t0 = self.rng(type)
        m0 = Model(value=t0)
        ser = m0.model_dump_json()
        m1 = Model.model_validate_json(ser)
        t1 = m1.value
        assert t0 == t1
    
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