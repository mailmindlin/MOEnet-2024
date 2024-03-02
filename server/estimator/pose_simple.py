from datetime import timedelta
from typing import Optional, TYPE_CHECKING
import logging

from wpiutil.log import DataLog

from worker.msg import AprilTagPose, MsgAprilTagDetections, PnpPose
from typedef.cfg import PoseEstimatorConfig, AprilTagStrategy
from wpi_compat.datalog import StructLogEntry
from typedef.geom import Transform3d, Pose3d, Translation3d, Rotation3d
from util.clock import Clock
from util.timestamp import Timestamp
from util.log import child_logger
from .util.types import Filter
from .util.lerp import lerp_pose3d, as_transform
from .util.interpolated import InterpolatingBuffer
from .util.cascade import Tracked
if TYPE_CHECKING:
	from .tf import ReferenceFrame

def as_tf_maybe(pose: Pose3d | None) -> Transform3d | None:
	if pose is None:
		return None
	return as_transform(pose)

class SimplePoseEstimator(Filter[int]):
	"""
	We need to merge together (often) conflicting views of the world.
	"""
	def __init__(self, config: PoseEstimatorConfig, clock: Clock, *, log: Optional[logging.Logger] = None, datalog: Optional[DataLog] = None) -> None:
		self.log = child_logger('pose', log)
		self.datalog = datalog
		self.config = config

		if self.datalog is not None:
			self.logFieldToRobot = StructLogEntry(datalog, 'raw/fieldToRobot', Pose3d)
			self.logFieldToOdom = StructLogEntry(datalog, 'raw/fieldToOdom', Pose3d)

		self.clock = clock
		self._last_o2r = Transform3d()
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
	
	def odom_to_robot(self) -> Transform3d:
		"Get the best estimated `odom`→`robot` corrective transform"
		samples_f2o = self.buf_field_to_odom.getInternalBuffer()
		samples_f2r = self.buf_field_to_robot.getInternalBuffer()

		# Return identity if we don't have any data
		if (len(samples_f2o) == 0) or (len(samples_f2r) == 0):
			self.log.debug("No data to compute odom→robot correction")
			return self._last_o2r
		
		# Find timestamps of overlapping range between field→odom and field→robot data
		first_f2o = samples_f2o[0][0]
		first_f2r = samples_f2r[0][0]
		ts_start = max(first_f2o, first_f2r)

		last_f2o = samples_f2o[-1][0]
		last_f2r = samples_f2r[-1][0]
		ts_end = min(last_f2o, last_f2r)
		if ts_end < ts_start:
			# No overlap
			self.log.debug("No overlap between field→odom and field→robot data")
			return self._last_o2r
		
		# We want the most recent pair that overlap
		f2o = self.buf_field_to_odom.sample(ts_end)
		assert f2o is not None
		f2r = self.buf_field_to_robot.sample(ts_end)
		assert f2r is not None
		
		res = Transform3d(f2o, f2r)
		self._last_o2r = res
		return res
	
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
	
	def track_tf(self, src: 'ReferenceFrame', dst: 'ReferenceFrame', ts: Timestamp) -> Tracked[Transform3d | None]:
		from .tf import ReferenceFrameKind
		match src.kind:
			case ReferenceFrameKind.FIELD:
				match dst.kind:
					case ReferenceFrameKind.ROBOT:
						if ts is None:
							return self.buf_field_to_robot.latest().map(as_tf_maybe)
						else:
							return self.buf_field_to_robot.track(ts).map(as_tf_maybe)
					case ReferenceFrameKind.ODOM:
						if ts is None:
							return self.buf_field_to_odom.latest().map(as_tf_maybe)
						else:
							return self.buf_field_to_odom.track(ts).map(as_tf_maybe)
			case ReferenceFrameKind.ODOM:
				match dst.kind:
					case ReferenceFrameKind.ROBOT:
						pass #TODO
		return NotImplemented
	
	def observe_f2r(self, timestamp: Timestamp, robot_to_camera: Transform3d, field_to_camera: Pose3d):
		"Record SLAM pose"
		field_to_robot = field_to_camera.transformBy(robot_to_camera.inverse())

		if self.datalog is not None:
			self.logFieldToRobot.append(field_to_robot, timestamp.as_wpi())
		
		self.buf_field_to_robot.add(timestamp, field_to_robot)

	def _select_apriltag_pose(self, timestamp: Timestamp, robot_to_camera: Transform3d, poses: list[PnpPose]) -> Pose3d | None:
		def is_reasonable(pose: Pose3d):
			if not self.config.force2d:
				return True
			# Z should be near the floor
			if not (-0.5 < pose.translation().Z() < 1):
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
		poses = [ep for ep in poses if is_reasonable(ep.fieldToCam)]

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
	
	def observe_apriltags(self, timestamp: Timestamp, robot_to_camera: Transform3d, detections: MsgAprilTagDetections):
		"Observe apriltag detections"
		field_to_camera = self._apriltags_to_pose(timestamp, robot_to_camera, detections)
		if field_to_camera is not None:
			self.observe_f2r(timestamp, robot_to_camera, field_to_camera)		
	
	def observe_f2o(self, timestamp: Timestamp, field_to_odom: Pose3d):
		"Record odometry pose"
		if self.datalog is not None:
			self.logFieldToOdom.append(field_to_odom, timestamp.as_wpi())
		
		self.buf_field_to_odom.add(timestamp, field_to_odom)
	
	def clear(self):
		self.buf_field_to_odom.clear()
		self.buf_field_to_robot.clear()
		self._last_o2r = Transform3d()
	
	def observe(self, measurement: int):
		pass
	
	def predict(self, now: Timestamp, delta: timedelta):
		pass