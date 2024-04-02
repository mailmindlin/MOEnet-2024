from typing import TYPE_CHECKING
from datetime import timedelta
from logging import Logger

if TYPE_CHECKING:
	from worker.controller import WorkerManager

from util.timestamp import Timestamp
from typedef.geom import Transform3d

from .util.cascade import Tracked, StaticValue
from .tf import ReferenceFrame, ReferenceFrameKind

class StaticCameraTracker:
	"Track a static camera (always returns a StaticValue)"
	def __init__(self, robot_to_camera: Transform3d) -> None:
		self.robot_to_camera = robot_to_camera
	
	def sample(self, timestamp: Timestamp | None) -> Tracked[Transform3d]:
		return StaticValue(self.robot_to_camera)

class DynamicCameraTracker:
	"Track a dynamic camera (interpolates over time)"
	def __init__(self, historyLength: timedelta, robot_to_camera: Transform3d) -> None:
		self.robot_to_camera = robot_to_camera
		from .util.interpolated import InterpolatingBuffer
		from .util.lerp import lerp_transform3d
		self.buffer = InterpolatingBuffer[Timestamp, Transform3d, timedelta](historyLength, lerp_transform3d)
	
	def sample(self, timestamp: Timestamp | None) -> Tracked[Transform3d]:
		if timestamp is None:
			return self.buffer.latest(self.robot_to_camera)
		else:
			return self.buffer.track(timestamp, self.robot_to_camera)

class CamerasTracker:
	"Track robot-to-camera transforms"
	def __init__(self, historyLength: timedelta, *, log: Logger, workers: 'WorkerManager | None' = None):
		self.log = log.getChild('camtrack')
		self.historyLength = historyLength
		self._camera_poses: list[StaticCameraTracker | DynamicCameraTracker] = list()
		"Camera trackers"
		self._nt_lookup: dict[str, DynamicCameraTracker] = dict()
		"NetworkTable lookups"

		if workers is not None:
			self.reset(workers)
	
	def reset(self, workers: 'WorkerManager'):
		"Reset with new workers"
		self._camera_poses.clear()
		self._nt_lookup.clear()
		for worker in workers:
			if worker.config.dynamic_pose is None:
				tracker = StaticCameraTracker(worker.config.robot_to_camera)
			else:
				tracker = DynamicCameraTracker(self.historyLength, worker.config.robot_to_camera)
				self._nt_lookup[worker.config.dynamic_pose] = tracker
			self._camera_poses.append(tracker)
	
	def record_r2c(self, nt_camera_name: str, robot_to_camera: Transform3d, timestamp: Timestamp):
		try:
			tracker = self._nt_lookup[nt_camera_name]
		except KeyError:
			self.log.warning('No dynamic pose for camera %s', nt_camera_name)
		return 

	def robot_to_camera(self, camera_id: int, timestamp: Timestamp | None) -> Tracked[Transform3d]:
		"Find robot-to-camera transform"
		tracker = self._camera_poses[camera_id]
		return tracker.sample(timestamp)
	
	def track_tf(self, src: ReferenceFrame, dst: ReferenceFrame, timestamp: Timestamp | None = None) -> Tracked[Transform3d]:
		if src.kind == ReferenceFrameKind.ROBOT and dst.kind == ReferenceFrameKind.CAMERA:
			return self.robot_to_camera(dst.idx, timestamp)
		return NotImplemented