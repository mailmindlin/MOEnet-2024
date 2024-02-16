from typing import TypeVar, Type
from random import Random
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
    "Make random type generator"
    rng = Random()
    def rand_t1(t: Type[T]) -> T:
        return rand_t(t, rng)
    return rand_t1