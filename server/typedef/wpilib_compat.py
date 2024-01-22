"Type definitions for communicating with WPIlib"
from typing import List
from typing_extensions import TypedDict
from pydantic import BaseModel
try:
    from .geom import Pose3d
except ImportError:
    from geom import Pose3d

class FieldLayout(TypedDict):
    length: float
    "Field length (meters)"
    width: float
    "Field width (meters)"

class FieldTag(BaseModel):
    ID: int
    pose: Pose3d

class AprilTagFieldJSON(BaseModel):
    "Format of WPIlib AprilTag JSON files"
    field: FieldLayout
    tags: List[FieldTag]