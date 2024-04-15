from typing import ClassVar, Protocol, Sequence
from dataclasses import dataclass
import enum

from typedef.geom import Transform3d, Pose3d
from util.timestamp import Timestamp, Stamped
from .util.cascade import Tracked, StaticValue

class ReferenceFrameKind(enum.Enum):
	FIELD = enum.auto()
	"Absolute field frame"
	ODOM = enum.auto()
	"Robot odometry position"
	ROBOT = enum.auto()
	"Robot position"
	CAMERA = enum.auto()
	DETECTION = enum.auto()

	@property
	def many(self):
		return self in (ReferenceFrameKind.CAMERA, ReferenceFrameKind.DETECTION)


@dataclass
class ReferenceFrame:
	FIELD: ClassVar['ReferenceFrame']
	ROBOT: ClassVar['ReferenceFrame']
	ODOM: ClassVar['ReferenceFrame']

	@staticmethod
	def camera(idx: int) -> 'ReferenceFrame':
		return ReferenceFrame(ReferenceFrameKind.CAMERA, idx)

	@staticmethod
	def detection(idx: int) -> 'ReferenceFrame':
		return ReferenceFrame(ReferenceFrameKind.DETECTION, idx)
	
	kind: ReferenceFrameKind
	idx: int = 0

ReferenceFrame.FIELD = ReferenceFrame(ReferenceFrameKind.FIELD)
ReferenceFrame.ROBOT = ReferenceFrame(ReferenceFrameKind.ROBOT)
ReferenceFrame.ODOM = ReferenceFrame(ReferenceFrameKind.ODOM)

class TfProvider(Protocol):
	"Data provider for [TfTracker]"
	@property
	def supported_conversions(self) -> Sequence[tuple[ReferenceFrame, ReferenceFrame]]:
		"Enumerate supported conversions"
		...

	def track_tf(self, base: ReferenceFrame, target: ReferenceFrame, timestamp: Timestamp | None = None) -> Tracked[Stamped[Transform3d] | None]:
		"""
		Track transform
		
		:param base: Base frame
		:param target: Target frame
		:param timestamp: When to get transform. If `None`, get the latest transform.

		Returns
		-------
		Stamped transform from src -> dst frame
		"""
		...


class TfTracker:
	def __init__(self, *providers: tuple[ReferenceFrameKind, ReferenceFrameKind, TfProvider]) -> None:
		self.providers = list(providers)

	# def track_all(self, src: ReferenceFrame, dst: ReferenceFrame, timestamp: Timestamp | None = None) -> Tracked[list[tuple[ReferenceFrame, Transform3d]]]:
	# 	pass

	def get_provider(self, src: ReferenceFrameKind, dst: ReferenceFrameKind) -> TfProvider:
		for src_kind, dst_kind, provider in self.providers:
			if src_kind == src and dst_kind == dst:
				return provider
		else:
			raise ValueError()

	def track_tf(self, base: ReferenceFrame, target: ReferenceFrame, timestamp: Timestamp | None = None) -> Tracked[Stamped[Transform3d] | None]:
		if base == target:
			# Identity
			return StaticValue(Stamped(Transform3d(), Timestamp.invalid()))
		
		if base.kind == target.kind:
			raise ValueError()
		
		provider = self.get_provider(base.kind, target.kind)
		return provider.track_tf(base, target, timestamp)
	
	def track_pose(self, dst: ReferenceFrame, timestamp: Timestamp | None = None) -> Tracked[Pose3d]:
		"Special case where we track_tf relative to the field"
		from .util.lerp import as_pose
		def as_pose_1(transform: Transform3d | None) -> Pose3d:
			if transform is None:
				# raise ValueError(f'Empty transform field -> {dst}')
				return Pose3d()
			return as_pose(transform)
		return self.track_tf(ReferenceFrame.FIELD, dst, timestamp=timestamp).map(as_pose_1)
