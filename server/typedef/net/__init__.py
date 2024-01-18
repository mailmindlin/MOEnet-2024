"Over-the-network datatypes"
from typing import TYPE_CHECKING
from enum import IntEnum

class Status(IntEnum):
	"Network Status"
	
	NOT_READY = 0
	"Waiting for initial config"
	INITIALIZING = 1
	"Setting up cameras"
	READY = 2
	SLEEPING = 3
	ERROR = 4
	FATAL = 5

# Add type hints for ProtoBuf autogens
if TYPE_CHECKING:
	from typing import Optional, List
	from dataclasses import dataclass
	@dataclass
	class Translation3d:
		x: Optional[float] = None
		y: Optional[float] = None
		z: Optional[float] = None
	
	@dataclass
	class Detection:
		timestamp: Optional[int] = None
		label_id: Optional[int] = None
		confidence: Optional[float] = None
		positionRobot: Optional[Translation3d] = None
		positionField: Optional[Translation3d] = None

	@dataclass
	class Detections:
		labels: Optional[List[str]] = None
		detections: Optional[List[Detection]] = None
else:
	from .Detections_pb2 import Translation3d, Detection, Detections