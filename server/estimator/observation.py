from typing import TypeAlias, Union, Annotated, Protocol

from pydantic import BaseModel, AllowInfNan
from annotated_types import Ge, Le

from util.timestamp import Timestamp
from typedef.geom_cov import Pose3dCov, Twist3dCov, Translation3dCov

from .tf import ReferenceFrame

class ObservationBase(BaseModel):
	ts: Timestamp
	"Timestamp when the observation happened"
	target_frame: ReferenceFrame
	"Measurement frame"
	
	# is_control: bool = False
	# "Is this a control term?"

class PoseObservation(BaseModel):
	"Position data"
	pose: Pose3dCov | None = None
	twist: Twist3dCov | None = None
	base_frame: ReferenceFrame
	"Transform base frame"


class AprilTagDetection(BaseModel):
	ID: int

class AprilTagObservation(BaseModel):
	"Camera AprilTag"
	pose: Pose3dCov | None
	detections: list[AprilTagDetection]

class ObjectDetectionEntry(BaseModel):
	label: str
	confidence: Annotated[float, Ge(0), Le(1), AllowInfNan(False)]
	pose: Translation3dCov

class ObjectDetectionObservation(BaseModel):
	"Object detection"
	detections: list[ObjectDetectionEntry]

type Observation = PoseObservation | AprilTagObservation | ObjectDetectionObservation

class DataSource(Protocol):
	name: str
	"Source name"
	frame: ReferenceFrame
	"Data reference frame"

class PoseEstimator[M, D: DataSource]:
	def get_source(self, name: str, frame: ReferenceFrame) -> D:
		...
	def observe(self, source: D, ts: Timestamp, value: M):
		...
	
	def predict(self, now: Timestamp):
		pass