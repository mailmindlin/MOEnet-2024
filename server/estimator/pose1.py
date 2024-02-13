from typing import Optional
import logging

from wpimath.interpolation._interpolation import TimeInterpolatablePose3dBuffer
from wpiutil.log import DataLog, DoubleArrayLogEntry, DoubleLogEntry

from worker.msg import MsgPose, AprilTagPose
from typedef.cfg import PoseEstimatorConfig, AprilTagStrategy
from wpi_compat.datalog import StructLogEntry
from typedef.geom import Transform3d, Pose3d, Translation3d, Rotation3d
from util.clock import Clock
from util.timestamp import Timestamp
from .util import interpolate_pose3d


class PoseEstimator:
	"""
	We need to merge together (often) conflicting views of the world.
	"""
	def __init__(self, config: PoseEstimatorConfig, clock: Clock, *, log: logging.Logger, datalog: Optional[DataLog] = None) -> None:
		self.log = log.getChild('pose')
		self.datalog = datalog
		self.config = config

		if self.datalog is not None:
			self.logFieldToRobot = DoubleArrayLogEntry(datalog, 'raw/fieldToRobot')
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

		self.buf_field_to_robot = TimeInterpolatablePose3dBuffer(pose_history, interpolate_pose3d)
		"Buffer for `field`→`robot` transforms (for sync with odometry)"
		self.buf_field_to_odom = TimeInterpolatablePose3dBuffer(pose_history, interpolate_pose3d)
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
		if res := self.buf_field_to_robot.sample(time.as_seconds()):
			return res
		# Return zero if we don't have any info
		return Pose3d()
	
	def field_to_odom(self, time: Timestamp) -> Pose3d:
		"Get the `field`→`odom` transform at a specified time"
		if res := self.buf_field_to_odom.sample(time.as_seconds()):
			return res
		# Return zero if we don't have any info
		return Pose3d()
	
	def record_f2r(self, timestamp: Timestamp, robot_to_camera: Transform3d, field_to_camera: Pose3d):
		"Record SLAM pose"
		field_to_robot = field_to_camera.transformBy(robot_to_camera.inverse())

		if self.datalog is not None:
			q = field_to_robot.rotation().getQuaternion()
			self.logFieldToRobot.append([field_to_robot.x, field_to_robot.y, field_to_robot.z, q.W(), q.X(), q.Y(), q.Z()], timestamp.as_wpi())
		
		self.buf_field_to_robot.addSample(timestamp.as_seconds(), field_to_robot)

	def _select_apriltag(self, timestamp: Timestamp, robot_to_camera: Transform3d, detections: list[AprilTagPose]) -> Pose3d | None:
		if len(detections) == 0:
			return None
		if len(detections) == 1:
			return detections[0].fieldToCam
		
		match self.config.apriltagStrategy:
			case AprilTagStrategy.LOWEST_AMBIGUITY:
				best_det = min(detections, key=lambda det: det.error)
				return best_det.fieldToCam
			case AprilTagStrategy.CLOSEST_TO_LAST_POSE:
				last_f2r = self.field_to_robot(timestamp)
				last_f2c = last_f2r.transformBy(robot_to_camera)
				best_det = min(detections, key=lambda det: det.camToTag.translation().distance(last_f2c.translation()))
				return best_det.fieldToCam
			case AprilTagStrategy.AVERAGE_BEST_TARGETS:
				tra = Translation3d()
				rot = Rotation3d()
				total_error = sum(1.0 / det.error for det in detections)
				for det in detections:
					weight = (1.0 / det.error) / total_error
					tra += det.camToTag.translation() * weight
					rot += det.camToTag.rotation() * weight
				return Pose3d(tra, rot)
	
	def record_apriltag(self, timestamp: Timestamp, robot_to_camera: Transform3d, detections: list[AprilTagPose]):
		field_to_camera = self._select_apriltag(timestamp, robot_to_camera, detections)
		if field_to_camera is not None:
			self.record_f2r(timestamp, robot_to_camera, field_to_camera)		
	
	def record_f2o(self, timestamp: Timestamp, field_to_odom: Pose3d):
		"Record odometry pose"
		if self.datalog is not None:
			self.logFieldToOdom.append(field_to_odom, timestamp.as_wpi())
		
		self.buf_field_to_odom.addSample(timestamp.as_seconds(), field_to_odom)
	
	def clear(self):
		self.buf_field_to_odom.clear()
		self.buf_field_to_robot.clear()
		self._last_o2r = Transform3d()