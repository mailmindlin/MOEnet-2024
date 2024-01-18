"Type definitions for communicating with WPIlib"
from typing import List
from typing_extensions import TypedDict
from pydantic import BaseModel

class FieldLayoutJSON(TypedDict):
    length: float
    "Field length (meters)"
    width: float
    "Field width (meters)"

class Translation3dJSON(TypedDict):
    x: float
    y: float
    z: float

class Quaternion3dJSON(TypedDict):
    W: float
    X: float
    Y: float
    Z: float

class Rotation3dJSON(TypedDict):
    quaternion: Quaternion3dJSON

class Pose3dJSON(TypedDict):
    translation: Translation3dJSON
    rotation: Rotation3dJSON

class FieldTagJSON(BaseModel):
    ID: int
    pose: Pose3dJSON

class AprilTagFieldJSON(BaseModel):
    field: FieldLayoutJSON
    tags: List[FieldTagJSON]