from typing import Optional, TYPE_CHECKING, Reversible, Iterable
from datetime import timedelta
from dataclasses import dataclass
import logging

from wpiutil.log import DataLog

from worker.msg import MsgAprilTagDetections, PnpPose
from typedef.cfg import PoseEstimatorConfig, AprilTagStrategy
from wpi_compat.datalog import StructLogEntry
from typedef.geom import Transform3d, Pose3d, Translation3d, Rotation3d
from typedef.geom_cov import Pose3dCov
from util.clock import Clock
from util.timestamp import Timestamp, Stamped
from util.log import child_logger
from .util.lerp import lerp_pose3d, as_transform
from .util.interpolated import InterpolatingBuffer, Comparable
from .util.cascade import Tracked, Derived
if TYPE_CHECKING:
	from .tf import ReferenceFrame

def as_tf_maybe(pose: Pose3d | None) -> Transform3d | None:
	if pose is None:
		return None
	return as_transform(pose)

# Collection helpers
def first[E](items: Iterable[E]) -> E:
	it = iter(items)
	return next(it)
def last[E](items: Reversible[E]) -> E:
	it = iter(reversed(items))
	return next(it)

def last_overlap[E: Comparable](a: Reversible[E], b: Reversible[E]) -> E | None:
	try:
		first_a = first(a)
		first_b = first(b)
	except StopIteration:
		# Something was empty
		return None
	start = max(first_a, first_b)

	last_a = last(a)
	last_b = last(b)
	end = min(last_a, last_b)

	if end < start:
		# No overlap
		return None
	return end

@dataclass
class OdomCorrectionEntry:
	mc_f2r: int
	mc_f2o: int
	timestamp: Timestamp | None
	trackers: tuple[Tracked[Pose3d | None], Tracked[Pose3d | None]] | None = None
	value: Transform3d | None = None

	def update(self, buf_f2r: InterpolatingBuffer[Timestamp, Pose3d, timedelta], buf_f2o: InterpolatingBuffer[Timestamp, Pose3d, timedelta], force: bool) -> 'OdomCorrectionEntry':
		mc_f2r = buf_f2r.modcount
		mc_f2o = buf_f2o.modcount
		if (self.mc_f2r == mc_f2r) and (self.mc_f2o == mc_f2o):
			# Buffers weren't modified -> no change
			return self
		next_ts = last_overlap(buf_f2r.keys(), buf_f2o.keys())
		if next_ts is None:
			# Early exit: we have no overlap
			return OdomCorrectionEntry(mc_f2r=mc_f2r, mc_f2o=mc_f2o, timestamp=next_ts)

		invalidated = (next_ts != self.timestamp)
		if (not invalidated) and (self.trackers is not None):
			robot, odom = self.trackers
		else:
			robot = None
			odom = None
		
		if (not force) and ((robot is None) or (odom is None)):
			# Exit early
			return OdomCorrectionEntry(mc_f2r=mc_f2r, mc_f2o=mc_f2o, timestamp=next_ts)
		if robot is None:
			robot = buf_f2r.track(next_ts)
			invalidated = True
		elif not robot.is_fresh:
			robot = robot.refresh()
			invalidated = True
		
		if odom is None:
			odom = buf_f2o.track(next_ts)
			invalidated = True
		elif not odom.is_fresh:
			odom = odom.refresh()
			invalidated = True
		
		if (not invalidated) and (self.value is not None):
			#TODO: self.value can be valid and None, but it's a representation issue so we don't know it
			value = self.value
		elif (robot.current is not None) and (odom.current is not None):
			value = robot.current - odom.current
			invalidated = True
		else:
			value = None
		
		if invalidated:
			return OdomCorrectionEntry(
				mc_f2r=mc_f2r,
				mc_f2o=mc_f2o,
				timestamp=next_ts,
				trackers=(robot, odom),
				value=value
			)
		else:
			return self

class TrackedOdomCorrection(Tracked[Stamped[Transform3d] | None]):
	_value: OdomCorrectionEntry
	_next: OdomCorrectionEntry
	def __init__(self, buf_f2r: InterpolatingBuffer[Timestamp, Pose3d, timedelta], buf_f2o: InterpolatingBuffer[Timestamp, Pose3d, timedelta]):
		self.buf_f2r = buf_f2r
		self.buf_f2o = buf_f2o
	
	@property
	def current(self):
		if not hasattr(self, '_value'):
			# Use refresh to compute first value
			self.refresh()
		value = self._value.value
		if value is None:
			return None
		ts = self._value.timestamp
		assert ts is not None
		return Stamped(value, ts)
	
	@property
	def is_fresh(self) -> bool:
		if hasattr(self, '_value'):
			self._next = self._next.update(self.buf_f2r, self.buf_f2o, force=False)
			return self._value is self._next
		else:
			# Initial value not calculated yet, we can't be out of date
			return True
	
	def refresh(self) -> Tracked[Stamped[Transform3d] | None]:
		if hasattr(self, '_value'):
			# No refresh needed
			self._next = self._next.update(self.buf_f2r, self.buf_f2o, True)
		else:
			self._value = OdomCorrectionEntry(self.buf_f2r.modcount - 1, self.buf_f2o.modcount - 1, None).update(self.buf_f2r, self.buf_f2o, force=True)
			self._next = self._value
		return self

def compute_odom_correction(field_to_robot: Pose3d, field_to_odom: Pose3d):
	# Return identity if we don't have any data
	# if (len(self.buf_field_to_odom) == 0) or (len(self.buf_field_to_robot) == 0):
	# 	self.log.debug("No data to compute odom→robot correction")
	# 	return self._last_o2r
	
	# Find timestamps of overlapping range between field→odom and field→robot data
	
	# overlap_ts = last_overlap(self.buf_field_to_odom.keys(), self.buf_field_to_robot.keys())
	# if overlap_ts is None:
	# 	# No overlap
	# 	self.log.debug("No overlap between field→odom and field→robot data")
	# 	return self._last_o2r
	
	# We want the most recent pair that overlap
	# f2o = self.buf_field_to_odom.sample(overlap_ts)
	# assert f2o is not None
	# f2r = self.buf_field_to_robot.sample(overlap_ts)
	# assert f2r is not None
	
	if field_to_odom is None:
		return None
	if field_to_robot is None:
		return None
	
	return field_to_robot - field_to_odom


class SimplePoseEstimator:
	"""
	We need to merge together (often) conflicting views of the world.
	"""
	def __init__(self, config: PoseEstimatorConfig, clock: Clock, *, log: Optional[logging.Logger] = None, datalog: Optional[DataLog] = None) -> None:
		self.log = child_logger('pose', log)
		self.datalog = datalog
		self.config = config

		if datalog is not None:
			self.logFieldToRobot = StructLogEntry(datalog, 'raw/fieldToRobot', Pose3d)
			self.logFieldToOdom = StructLogEntry(datalog, 'raw/fieldToOdom', Pose3d)

		self.clock = clock
		self._last_o2r = Stamped(Transform3d(), Timestamp.invalid())
		"Last `odom`→`robot` (for caching `odom_to_robot()`)"

		pose_history = config.history.total_seconds()
		if pose_history < 0:
			self.log.error("Negative pose history (%s). Default to zero.", config.history)
			pose_history = 0
		elif pose_history == 0:
			self.log.warning("No pose history (syncing f2r and f2o may not work right)")

		# self.buf_field_to_robot = TimeInterpolatablePose3dBuffer(pose_history, lerp_pose3d)
		self.buf_field_to_robot = InterpolatingBuffer[Timestamp, Pose3d, timedelta](config.history, lerp_pose3d)
		"Buffer for `field`→`robot` transforms (for sync with odometry)"
		# self.buf_field_to_odom = TimeInterpolatablePose3dBuffer(pose_history, lerp_pose3d)
		self.buf_field_to_odom = InterpolatingBuffer[Timestamp, Pose3d, timedelta](config.history, lerp_pose3d)
		"Buffer for `field`→`odom` transforms (for sync with absolute pose)"

	def _cache_latest_o2r(self, value: Stamped[Transform3d] | None) -> Stamped[Transform3d]:
		if value is None:
			return self._last_o2r
		self._last_o2r = value
		return value
	
	def latest_odom_to_robot(self) -> Tracked[Stamped[Transform3d]]:
		return TrackedOdomCorrection(self.buf_field_to_robot, self.buf_field_to_odom).map(self._cache_latest_o2r)
	
	def odom_to_robot(self, timestamp: Timestamp) -> Tracked[Transform3d]:
		"Get the best estimated `odom`→`robot` corrective transform"
		# At a specific timestamp
		tracked_f2o = self.buf_field_to_odom.track(timestamp)
		tracked_f2r = self.buf_field_to_robot.track(timestamp)

		return Derived(compute_odom_correction, tracked_f2r, tracked_f2o)
		
	
	def field_to_robot(self, time: Timestamp) -> Pose3d:
		"Get the `field`→`robot` transform at a specified time"
		assert isinstance(time, Timestamp)
		time.assert_src(self.clock)
		
		if res := self.buf_field_to_robot.sample(time):
			return res
		# Return zero if we don't have any info
		return Pose3d()
	
	def field_to_odom(self, time: Timestamp) -> Pose3d:
		"Get the `field`→`odom` transform at a specified time"
		# Return zero if we don't have any info
		return self.buf_field_to_odom.get(time, Pose3d())
	
	def track_tf(self, src: 'ReferenceFrame', dst: 'ReferenceFrame', timestamp: Timestamp | None = None) -> Tracked[Transform3d | None]:
		from .tf import ReferenceFrameKind
		match src.kind:
			case ReferenceFrameKind.FIELD:
				match dst.kind:
					case ReferenceFrameKind.ROBOT:
						if timestamp is None:
							return self.buf_field_to_robot.latest().map(as_tf_maybe)
						else:
							return self.buf_field_to_robot.track(timestamp).map(as_tf_maybe)
					case ReferenceFrameKind.ODOM:
						if timestamp is None:
							return self.buf_field_to_odom.latest().map(as_tf_maybe)
						else:
							return self.buf_field_to_odom.track(timestamp).map(as_tf_maybe)
			case ReferenceFrameKind.ODOM:
				match dst.kind:
					case ReferenceFrameKind.ROBOT:
						return self.odom_to_robot()
						raise NotImplementedError()
		return NotImplemented
	
	def observe_f2r(self, timestamp: Timestamp, robot_to_camera: Tracked[Transform3d], field_to_camera: Pose3dCov):
		"Record SLAM pose"
		
		robot_to_camera_val = robot_to_camera.current
		field_to_robot = field_to_camera.transformBy(robot_to_camera_val.inverse()).mean

		if self.datalog is not None:
			self.logFieldToRobot.append(field_to_robot, timestamp.as_wpi())
		
		self.buf_field_to_robot.add(timestamp, field_to_robot)

	def _select_apriltag_pose(self, timestamp: Timestamp, robot_to_camera: Transform3d, poses: list[PnpPose]) -> Pose3d | None:
		def is_reasonable(pose: Pose3d):
			if not self.config.force2d:
				return True
			# Z should be near the floor
			if not (-1 < pose.translation().Z() < 1):
				self.log.info("Reject pose: invalid z %s", pose)
				return False
			# Roll should be <30º
			if not (-0.5 < pose.rotation().X() < 0.5):
				self.log.info("Reject pose: invalid X %s", pose)
				return False
			# Pitch should be <30º
			if not (-0.5 < pose.rotation().Y() < 0.5):
				self.log.info("Reject pose: invalid Y %s", pose)
				return False
			# Yaw can be whatever
			return True
		
		# Filter only reasonable 2d poses
		poses = [
			pose
			for pose in poses
			if is_reasonable(pose.fieldToCam)
		]

		if len(poses) == 0:
			return None
		if len(poses) == 1:
			return poses[0].fieldToCam
		
		match self.config.apriltagStrategy:
			case AprilTagStrategy.LOWEST_AMBIGUITY:
				best_det = min(poses, key=lambda pose: pose.error)
				return best_det.fieldToCam
			case AprilTagStrategy.CLOSEST_TO_LAST_POSE:
				last_f2r = self.field_to_robot(timestamp.before())
				last_f2c = last_f2r.transformBy(robot_to_camera).translation()
				best_det = min(poses, key=lambda det: det.fieldToCam.translation().distance(last_f2c))
				return best_det.fieldToCam
			case AprilTagStrategy.AVERAGE_BEST_TARGETS:
				tra = Translation3d()
				rot = Rotation3d()
				total_error = sum(1.0 / pose.error for pose in poses)
				for pose in poses:
					weight = (1.0 / pose.error) / total_error
					tra += pose.fieldToCam.translation() * weight
					rot += pose.fieldToCam.rotation() * weight
				return Pose3d(tra, rot)
	
	def _apriltags_to_pose(self, timestamp: Timestamp, robot_to_camera: Transform3d, msg: MsgAprilTagDetections) -> Pose3d | None:
		res = None
		# Use PnP if possible
		if msg.pnp is not None:
			res = self._select_apriltag_pose(timestamp, robot_to_camera, msg.pnp.poses)
		
		if res is None:
			valid_dets = [
				PnpPose(error=det.error, fieldToCam=det.fieldToCam)
				for det in msg.detections
				if det.fieldToCam is not None
			]
			res = self._select_apriltag_pose(timestamp, robot_to_camera, valid_dets)
		
		return res
	
	def observe_apriltags(self, timestamp: Timestamp, robot_to_camera: Tracked[Transform3d], detections: MsgAprilTagDetections):
		"Observe apriltag detections"
		self.log.info("Observe apriltags %s", detections)
		field_to_camera = self._apriltags_to_pose(timestamp, robot_to_camera.current, detections)
		if field_to_camera is not None:
			self.observe_f2r(timestamp, robot_to_camera, Pose3dCov(field_to_camera))		
	
	def observe_f2o(self, timestamp: Timestamp, field_to_odom: Pose3d):
		"Record odometry pose"
		if self.datalog is not None:
			self.logFieldToOdom.append(field_to_odom, timestamp.as_wpi())
		
		self.buf_field_to_odom.add(timestamp, field_to_odom)
	
	def clear(self):
		self.buf_field_to_odom.clear()
		self.buf_field_to_robot.clear()
		self._last_o2r = Stamped(Transform3d(), Timestamp.invalid())
	
	def observe(self, measurement: int):
		pass
	
	def predict(self, now: Timestamp, delta: timedelta):
		pass