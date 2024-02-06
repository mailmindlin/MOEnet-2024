from typing import Optional
import logging

from wpimath.interpolation._interpolation import TimeInterpolatablePose3dBuffer
from wpiutil.log import DataLog

from worker.msg import MsgPose
from typedef.cfg import EstimatorConfig
from wpi_compat.datalog import StructLogEntry
from typedef.geom import Transform3d, Pose3d
from util.clock import Clock
from util.timestamp import Timestamp
from .util import interpolate_pose3d


class PoseEstimator:
	"""
	We need to merge together (often) conflicting views of the world.
	"""
	def __init__(self, config: EstimatorConfig, clock: Clock, *, log: logging.Logger, datalog: Optional[DataLog] = None) -> None:
		self.log = log.getChild('pose')
		self.datalog = datalog
		self.config = config

		if self.datalog is not None:
			self.logFieldToRobot = StructLogEntry(datalog, 'raw/fieldToRobot', Pose3d)
			self.logFieldToOdom = StructLogEntry(datalog, 'raw/fieldToOdom', Pose3d)

		self.clock = clock
		self._last_o2r = Transform3d()
		"Last `odom`→`robot` (for caching `odom_to_robot()`)"

		pose_history = config.pose_history.total_seconds()
		if pose_history < 0:
			self.log.error("Negative pose history (%s). Default to zero.", config.pose_history)
			pose_history = 0
		elif pose_history == 0:
			self.log.warning("No pose history (syncing f2r and f2o may not work right)")

		self.buf_field_to_robot = TimeInterpolatablePose3dBuffer(config.pose_history.total_seconds(), interpolate_pose3d)
		"Buffer for `field`→`robot` transforms (for sync with odometry)"
		self.buf_field_to_odom = TimeInterpolatablePose3dBuffer(config.pose_history.total_seconds(), interpolate_pose3d)
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
	
	def record_f2r(self, robot_to_camera: Transform3d, msg: MsgPose):
		"Record SLAM pose"
		field_to_camera = msg.pose
		field_to_robot = field_to_camera.transformBy(robot_to_camera.inverse())
		timestamp = Timestamp.from_nanos(msg.timestamp)

		if self.datalog is not None:
			self.logFieldToRobot.append(field_to_robot, timestamp.as_wpi())
		
		self.buf_field_to_robot.addSample(timestamp.as_seconds(), field_to_robot)
	
	def record_f2o(self, timestamp: Timestamp, field_to_odom: Pose3d):
		"Record odometry pose"
		if self.datalog is not None:
			self.logFieldToOdom.append(field_to_odom, timestamp.as_wpi())
		
		self.buf_field_to_odom.addSample(timestamp.as_seconds(), field_to_odom)
	
	def clear(self):
		self.buf_field_to_odom.clear()
		self.buf_field_to_robot.clear()
		self._last_o2r = Transform3d()