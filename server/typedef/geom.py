from pydantic import BaseModel

class Vector3(BaseModel):
    x: float
    y: float
    z: float

class Quaternion(BaseModel):
    w: float
    x: float
    y: float
    z: float

class Pose(BaseModel):
    translation: Vector3
    rotation: Quaternion

class Twist(BaseModel):
    velocity: Vector3
    rotation: Vector3