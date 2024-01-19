"Over-the-network datatypes"
from typing import TYPE_CHECKING
from enum import IntEnum
from dataclasses import dataclass
from wpiutil import wpistruct
from wpimath import geometry

if TYPE_CHECKING:
	import numpy as np
	from typing_extensions import Buffer


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


@wpistruct.make_wpistruct
@dataclass
class Instant:
	s: wpistruct.int64
	ns: wpistruct.int32

@wpistruct.make_wpistruct
@dataclass
class Mat66:
	m0: wpistruct.double
	m1: wpistruct.double
	m2: wpistruct.double
	m3: wpistruct.double
	m4: wpistruct.double
	m5: wpistruct.double
	m6: wpistruct.double
	m7: wpistruct.double
	m8: wpistruct.double
	m9: wpistruct.double
	m10: wpistruct.double
	m11: wpistruct.double
	m12: wpistruct.double
	m13: wpistruct.double
	m14: wpistruct.double
	m15: wpistruct.double
	m16: wpistruct.double
	m17: wpistruct.double
	m18: wpistruct.double
	m19: wpistruct.double
	m20: wpistruct.double
	m21: wpistruct.double
	m22: wpistruct.double
	m23: wpistruct.double
	m24: wpistruct.double
	m25: wpistruct.double
	m26: wpistruct.double
	m27: wpistruct.double
	m28: wpistruct.double
	m29: wpistruct.double
	m30: wpistruct.double
	m31: wpistruct.double
	m32: wpistruct.double
	m33: wpistruct.double
	m34: wpistruct.double
	m35: wpistruct.double

	@staticmethod
	def from_np(src: 'np.ndarray'):
		return Mat66(*src.flatten())

# Fix Twist3d struct missing
def _make_twist3d_descriptor():
	from struct import Struct
	twist3d_struct = Struct('<dddddd')
	def _pack(value: geometry.Twist3d) -> bytes:
		return twist3d_struct.pack(
			value.dx,
			value.dy,
			value.dz,
			value.rx,
			value.ry,
			value.rz,
		)
	def _packinto(value: geometry.Twist3d, buffer: 'Buffer'):
		return twist3d_struct.pack_into(
			buffer,
			0,
			value.dx,
			value.dy,
			value.dz,
			value.rx,
			value.ry,
			value.rz,
		)
	def _unpack(b: 'Buffer') -> geometry.Twist3d:
		dx, dy, dz, rx, ry, rz = twist3d_struct.unpack(b)
		return geometry.Twist3d(dx, dy, dz, rx, ry, rz)
	return wpistruct.StructDescriptor(
		'struct:Twist3d',
		"double dx;double dy;double dz;double rx;double ry;double rz",
		8 * 6,
		_pack,
		_packinto,
		_unpack,
		None
	)
geometry.Twist3d.WPIStruct = _make_twist3d_descriptor()


@wpistruct.make_wpistruct
@dataclass
class PositionEstimate:
	ts: Instant
	pose: geometry.Pose3d
	poseCov: Mat66
	twist: geometry.Twist3d
	twistCov: Mat66


# Add type hints for ProtoBuf autogens
if TYPE_CHECKING:
	from typing import Optional, List
	from dataclasses import dataclass
	@dataclass
	class Timestamp:
		seconds: Optional[int] = None
		nanos: Optional[int] = None
	
	@dataclass
	class Translation3d:
		x: Optional[float] = None
		y: Optional[float] = None
		z: Optional[float] = None
	
	@dataclass
	class ObjectDetection:
		timestamp: Optional[Timestamp] = None
		label_id: Optional[int] = None
		confidence: Optional[float] = None
		positionRobot: Optional[Translation3d] = None
		positionField: Optional[Translation3d] = None

	@dataclass
	class ObjectDetections:
		labels: Optional[List[str]] = None
		detections: Optional[List[ObjectDetection]] = None
else:
	from .Detections_pb2 import Timestamp, Translation3d, ObjectDetection, ObjectDetections