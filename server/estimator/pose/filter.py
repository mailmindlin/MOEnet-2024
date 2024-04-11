from typing import Literal
from enum import IntFlag
from dataclasses import dataclass
from collections import deque
import logging
from functools import reduce
from enum import Enum, auto
from datetime import timedelta

import numpy as np
from server.typedef.geom import Transform3d
from server.typedef.geom_cov import Twist3dCov

from typedef.geom import Transform3d, Rotation3d, Pose3d, Twist3d
from typedef.geom_cov import Acceleration3dCov, Twist3dCov, Pose3dCov, rot3_to_mat, rot3_to_mat6, Odometry
from util.timestamp import Timestamp, Stamped
from util.clock import WallClock
from .base import ControlMembers, StateMembers, Measurement, block
from .ekf import EKF
from ..util.heap import Heap

def update_counts(acc: dict[StateMembers, int], updates: StateMembers, mask: StateMembers, map: StateMembers | None = None):
	if map is None:
		map = mask
	assert len(map) == len(mask)
	for u, v in zip(mask, map):
		if u in updates:
			acc[v] += 1

class SensorMode(Enum):
	ABSOLUTE = auto()
	RELATIVE = auto()
	DIFFERENTIAL = auto()

class DataSource[T]:
	name: str
	robot_to_sensor: Transform3d
	initial_measurement: Transform3d | None = None
	remove_gravitational_acceleration: bool = False
	last_message_time: Timestamp | None = None
	previous_measurement: Measurement | None = None

	def __init__(self, estimator: 'PoseEstimator', name: str, robot_to_sensor: Transform3d) -> None:
		self._last_message_time = None
		self.estimator = estimator
		self.name = name
		self.robot_to_sensor = robot_to_sensor
	
	@property
	def sensor_to_robot(self) -> Transform3d:
		return self.robot_to_sensor.inverse()
	
	def measure(self, msg: T):
		pass


class OdometrySource(DataSource[Odometry]):
	def __init__(self, estimator: 'PoseEstimator', name: str, robot_to_sensor: Transform3d) -> None:
		super().__init__(estimator, name, robot_to_sensor)
	def measure(self, msg: Odometry):
		pass

class PoseSource(DataSource[Stamped[Twist3dCov]]):
	def __init__(self, estimator: 'PoseEstimator', name: str, robot_to_sensor: Transform3d, pose_threshold: float | None, mode: SensorMode) -> None:
		super().__init__(estimator, name, robot_to_sensor)
		self.pose_threshold = pose_threshold
		self.mode = mode
	
	def measure(self, msg: Stamped[Twist3dCov]):
		self.estimator.handle_pose(
			self.pose_update,
			self.pose_threshold,
			self,
			msg.value,
			msg.ts,
			self.mode,
		)

class TwistSource(DataSource[Stamped[Twist3dCov]]):
	def __init__(self, estimator: 'PoseEstimator', name: str, robot_to_sensor: Transform3d, twist_update: StateMembers, twist_threshold: float | None) -> None:
		super().__init__(estimator, name, robot_to_sensor)
		self.twist_threshold = twist_threshold
		self.twist_update = twist_update
	
	def measure(self, msg: Stamped[Twist3dCov]):
		self.estimator.handle_twist(
			self.twist_update,
			self.twist_threshold,
			self,
			msg.value,
			msg.ts,
		)

class IMUSource(DataSource[Stamped[Twist3dCov]]):
	def __init__(self, estimator: 'PoseEstimator', name: str, robot_to_sensor: Transform3d, pose_threshold: float | None, twist_threshold: float | None, linac_threshold: float | None, remove_gravity: bool, mode: SensorMode):
		super().__init__(estimator, name, robot_to_sensor)
		self.pose_threshold = pose_threshold
		self.twist_threshold = twist_threshold
		self.mode = mode

class PoseEstimatorConfig:
	publish_transform: bool = True
	publish_acceleration: bool = False
	permit_corrected_publication: bool = False
	reset_on_time_jump: bool = False
	use_control: bool = False

	smooth_lagged_data: bool = False
	history_length: timedelta = timedelta(seconds=0.0)
	force_2d: bool = False
	update_frequency: float = 30
	publish_transform = True
	predict_to_current_time: bool = False
	"""
	By default, the filter predicts and corrects up to the time of the
	latest measurement. If this is set to true, the filter does the same, but
	then also predicts up to the current time step.
	"""
	acceleration_limits: tuple[float, float, float, float, float, float] | None = None
	acceleration_gains: tuple[float, float, float, float, float, float] | None = None
	deceleration_limits: tuple[float, float, float, float, float, float] | None = None
	deceleration_gains: tuple[float, float, float, float, float, float] | None = None


# Utility functions
def mask(members: IntFlag) -> np.ndarray[float, tuple[Literal[3], Literal[3]]]:
	pass
	

class PoseEstimator:
	def __init__(self, config: PoseEstimatorConfig):
		self._sources: list[DataSource] = list()
		self.log = logging.getLogger("pose")
		self._filter = EKF()
		self.config = config
		self.clock = WallClock()

		self._last_set_pose_ts = Timestamp.invalid()
		self._last_diag_time = self.clock.now()
		self._last_diff_time = Timestamp.invalid(self.clock)

		self._sources: list[DataSource] = list()
		self._measurement_queue: Heap[Measurement] = Heap()
		self._filter_state_history = list()
		self._measurement_history: deque[Measurement] = deque()
		
		self._toggled_on = True

		self.twist_var_counts = {
			key: 0
			for key in StateMembers.TWIST
		}
		self.abs_pose_var_counts = {
			key: 0
			for key in StateMembers.POSE
		}

		# Optional acceleration publisher
		# if self._publish_acceleration:
		# 	accel_pub_ = this.create_publisher<geometry_msgs.msg.AccelWithCovarianceStamped>("accel/filtered", rclcpp.QoS(10), publisher_options)
	
	def initialize(self):
		# Init the last measurement time so we don't get a huge initial delta
		self._filter.last_measurement_time = self.clock.now()
		
	def set_pose(self, msg: Stamped[Pose3dCov]):
		# RCLCPP_INFO_STREAM(
		# 	get_logger(),
		# 	"Received set_pose request with value\n" << geometry_msgs.msg.to_yaml(*msg))

		# Get rid of any initial poses (pretend we've never had a measurement)
		for source in self._sources:
			source.initial_measurement = None
			source.previous_measurement = None
		
		self._measurement_queue.clear()
		self._filter_state_history.clear()
		self._measurement_history.clear()

		# Also set the last set pose time, so we ignore all messages
		# that occur before it

		self._last_set_pose_ts = msg.ts

		# Set the state vector to the reported pose
		ALL = reduce(lambda a, b: a|b, StateMembers)
		source: DataSource = None
		measurement = Measurement(msg.ts, source, update_vector=ALL)
		# We only measure pose variables, so initialize the vector to 0
		measurement.measure(ALL, 0.0, 1e-6)

		# Prepare the pose data (really just using this to transform it into the
		# target frame). Twist data is going to get zeroed out.
		# Since pose messages do not provide a child_frame_id, it defaults to baseLinkFrameId_
		measurement = self.prepare_pose(source, msg, StateMembers.POSE, SensorMode.ABSOLUTE)
		assert measurement

		# For the state
		self._filter.state = measurement.mean_dense
		self._filter.estimate_error_covariance = measurement.covariance_dense

		self._filter.last_measurement_time = self.clock.now()

	def make_odom(self, name: str, robot_to_sensor: Transform3d, update: StateMembers, pose_threshold: float | None = None, twist_threshold: float | None = None, mode: SensorMode = SensorMode.ABSOLUTE):
		# Now pull in its boolean update vector configuration. Create separate
		# vectors for pose and twist data, and then zero out the opposite values
		# in each vector (no pose data in the twist update vector and
		# vice-versa).
		pose_update_vec = update & ~StateMembers.TWIST
		twist_update_vec = update & ~StateMembers.POSE

		pose_update_sum = len(pose_update_vec)
		twist_update_sum = len(twist_update_vec)

		# Store the odometry topic subscribers so they don't go out of scope.
		if len(pose_update_vec | twist_update_vec) == 0:
			self.log.warning("%s is listed as an input topic, but all update variables are false", name)
			return DataSource(
				self,
				name,
				robot_to_sensor
			)

		if (pose_update_sum > 0):
			if mode == SensorMode.DIFFERENTIAL:
				update_counts(self.twist_var_counts, pose_update_vec, StateMembers.POSE, StateMembers.TWIST)
			else:
				update_counts(self.abs_pose_var_counts, pose_update_vec, StateMembers.POSE)

		if twist_update_sum > 0:
			update_counts(self.twist_var_counts, pose_update_vec, StateMembers.TWIST)

		# self.log.info(
		# 	"Subscribed to " <<
		# 	odom_topic << " (" << odom_topic_name << ")\n\t" <<
		# 	odom_topic_name << "_differential is " <<
		# 	(differential ? "true" : "false") << "\n\t" << odom_topic_name <<
		# 	"_pose_rejection_threshold is " << pose_mahalanobis_thresh <<
		# 	"\n\t" << odom_topic_name << "_twist_rejection_threshold is " <<
		# 	twist_mahalanobis_thresh << "\n\t" << odom_topic_name <<
		# 	" pose update vector is " << pose_update_vec << "\t" <<
		# 	odom_topic_name << " twist update vector is " <<
		# 	twist_update_vec);
		res = OdometrySource(
			self,
			name,
			robot_to_sensor,
		)
		self._sources.append(res)
		return res
	
	def make_pose(self, name: str, robot_to_sensor: Transform3d, update: StateMembers, pose_threshold: float | None = None, mode: SensorMode = SensorMode.ABSOLUTE) -> DataSource[Stamped[Pose3dCov]]:
		update = update & (~StateMembers.TWIST) & (~StateMembers.ACC_LIN)

		pose_update_sum = len(update)
		if pose_update_sum == 0:
			self.log.warning("%s is listed as an input topic, but all pose update variables are false", name)
			return DataSource(self, name, robot_to_sensor)

		if mode == SensorMode.DIFFERENTIAL:
			update_counts(self.twist_var_counts, update, StateMembers.POSE, StateMembers.TWIST)
		else:
			update_counts(self.abs_pose_var_counts, update, StateMembers.POSE)
		
		res = PoseSource(
			self,
			name,
			robot_to_sensor,
			pose_threshold,
			mode
		)
		# RF_DEBUG(
		# 	"Subscribed to " << pose_topic << " (" << pose_topic_name << ")\n\t" <<
		# 	pose_topic_name << "_differential is " <<
		# 	(differential ? "true" : "false") << "\n\t" << pose_topic_name <<
		# 	"_rejection_threshold is " << pose_mahalanobis_thresh <<
		# 	"\n\t" << pose_topic_name << " update vector is " <<
		# 	pose_update_vec);
		self._sources.append(res)
		return res

	def make_twist(self, name: str, robot_to_sensor: Transform3d, update: StateMembers, twist_threshold: float | None = None) -> DataSource[Stamped[Twist3dCov]]:
		# Pull in the sensor's config, zero out values that are invalid for the
		# twist type
		update = update & ~StateMembers.POSE
		update_counts(self.twist_var_counts, update, StateMembers.TWIST)
		twist_update_sum = len(update)
		if twist_update_sum == 0:
			self.log.warning("%s is listed as an input topic, but all pose update variables are false", name)
			return DataSource(self, name, robot_to_sensor)
		
		res = TwistSource(
			self,
			name,
			robot_to_sensor,
			twist_threshold
		)
		self._sources.append(res)
		return res
	
	def make_imu(self, name: str, robot_to_sensor: Transform3d, update: StateMembers, pose_threshold: float | None = None, twist_threshold: float | None = None, linac_threshold: float | None = None, remove_gravity: bool = False, mode: SensorMode = SensorMode.ABSOLUTE):
		# sanity checks for update config settings
		position_update_vec = update & StateMembers.POS_LIN
		if len(position_update_vec) > 0:
			self.log.warning("Some position entries in parameter %s config are set to "
				"true, but the sensor_msgs/Imu message contains no positional data", name)
		
		linear_velocity_update_vec = update & StateMembers.VEL_LIN
		if len(linear_velocity_update_vec) > 0:
			self.log.warning("Some position entries in parameter %s config are set to "
				"true, but the sensor_msgs/Imu message contains no linear velocity data", name)

		# IMU message contains no information about position, filter everything
		# except orientation
		pose_update_vec = update & StateMembers.POS_ANG

		# IMU message contains no information about linear speeds, filter
		# everything except angular velocity
		twist_update_vec = update & StateMembers.VEL_ANG

		accel_update_vec = update & StateMembers.ACC_LIN

		# Check if we're using control input for any of the acceleration
		# variables; turn off if so
		if self.control_update_vector[ControlMembers.Vx.idx()] and accel_update_vec[StateMembers.Ax.idx()]:
			self.log.error("X acceleration is being measured from IMU; X velocity control input is disabled")
			self.control_update_vector[ControlMembers.Vx.idx()] = False
		if self.control_update_vector[ControlMembers.Vy.idx()] and accel_update_vec[StateMembers.Ay.idx()]:
			self.log.error("Y acceleration is being measured from IMU; Y velocity control input is disabled")
			self.control_update_vector[ControlMembers.Vy.idx()] = False
		if self.control_update_vector[ControlMembers.Vz.idx()] and accel_update_vec[StateMembers.Az.idx()]:
			self.log.error("Z acceleration is being measured from IMU; Z velocity control input is disabled")
			self.control_update_vector[ControlMembers.Vz.idx()] = False

		if len(pose_update_vec | twist_update_vec | accel_update_vec) == 0:
			self.log.warning("%s is listed as an input topic, but all pose update variables are false", name)
			return DataSource(self, name, robot_to_sensor)

		if len(pose_update_vec) > 0:
			if mode == SensorMode.DIFFERENTIAL:
				update_counts(self.twist_var_counts, pose_update_vec, StateMembers.POS_ANG, StateMembers.VEL_ANG)
			else:
				update_counts(self.abs_pose_var_counts, pose_update_vec, StateMembers.POS_ANG)

		if len(twist_update_vec) > 0:
			update_counts(self.twist_var_counts, twist_update_vec, StateMembers.VEL_ANG)

		# RF_DEBUG(
		# 	"Subscribed to " <<
		# 	imu_topic << " (" << imu_topic_name << ")\n\t" <<
		# 	imu_topic_name << "_differential is " <<
		# 	(differential ? "true" : "false") << "\n\t" << imu_topic_name <<
		# 	"_pose_rejection_threshold is " << pose_mahalanobis_thresh <<
		# 	"\n\t" << imu_topic_name << "_twist_rejection_threshold is " <<
		# 	twist_mahalanobis_thresh << "\n\t" << imu_topic_name <<
		# 	"_linear_acceleration_rejection_threshold is " <<
		# 	accel_mahalanobis_thresh << "\n\t" << imu_topic_name <<
		# 	"_remove_gravitational_acceleration is " <<
		# 	(remove_grav_acc ? "true" : "false") << "\n\t" <<
		# 	imu_topic_name << " pose update vector is " << pose_update_vec <<
		# 	"\t" << imu_topic_name << " twist update vector is " <<
		# 	twist_update_vec << "\t" << imu_topic_name <<
		# 	" acceleration update vector is " << accel_update_vec);
		res = IMUSource(
			self,
			name,
			robot_to_sensor,
			pose_threshold,
			twist_threshold,
			linac_threshold,
			remove_gravity,
			mode,
		)
		self._sources.append(res)
		return res
	
	def poll(self):
		cur_time = self.clock.now()

		if self._toggled_on:
			# Now we'll integrate any measurements we've received if requested,
			# and update angular acceleration.
			self._integrate_measurements(cur_time)
			self._differentiate_measurements(cur_time)
		else:
			# Clear out measurements since we're not currently processing new entries
			self._measurement_queue.clear()

			# Reset last measurement time so we don't get a large time delta on toggle
			if self._filter.is_initialized:
				self._filter.last_measurement_time = self.clock.now()

		# Get latest state and publish it
		corrected_data = False
		if filtered_position := self.getFilteredOdometryMessage():
			#TODO
			# world_base_link_trans_msg_.header.stamp =
			# static_cast<rclcpp.Time>(filtered_position.header.stamp) + tf_time_offset_
			# world_base_link_trans_msg_.header.frame_id =
			# filtered_position.header.frame_id
			# world_base_link_trans_msg_.child_frame_id =
			# filtered_position.child_frame_id

			# world_base_link_trans_msg_.transform.translation.x =
			# filtered_position.pose.pose.position.x
			# world_base_link_trans_msg_.transform.translation.y =
			# filtered_position.pose.pose.position.y
			# world_base_link_trans_msg_.transform.translation.z =
			# filtered_position.pose.pose.position.z
			# world_base_link_trans_msg_.transform.rotation =
			# filtered_position.pose.pose.orientation

			# The filtered_position is the message containing the state and covariances:
			# nav_msgs Odometry
			if not self.validateFilterOutput(filtered_position):
				self.log.error(
					"Critical Error, NaNs were detected in the output state of the filter. "
					"This was likely due to poorly coniditioned process, noise, or sensor "
					"covariances.")

			# If we're trying to publish with the same time stamp, it means that we had a measurement get
			# inserted into the filter history, and our state estimate was updated after it was already
			# published. As of ROS Noetic, TF2 will issue warnings whenever this occurs, so we make this
			# behavior optional. Just for safety, we also check for the condition where the last published
			# stamp is *later* than this stamp. This should never happen, but we should handle the case
			# anyway.
			corrected_data = (not self.config.permit_corrected_publication and self._last_published_stamp >= filtered_position.header.stamp)

			# If the world_frame_id_ is the odom_frame_id_ frame, then we can just
			# send the transform. If the world_frame_id_ is the map_frame_id_ frame,
			# we'll have some work to do.
			if (self.config.publish_transform and not corrected_data):
				if filtered_position.header.frame_id == odom_frame_id_:
					world_transform_broadcaster_.sendTransform(world_base_link_trans_msg_)
				elif (filtered_position.header.frame_id == map_frame_id_):
					try:
						tf2.Transform world_base_link_trans
						tf2.fromMsg(
							world_base_link_trans_msg_.transform,
							world_base_link_trans)

						tf2.Transform base_link_odom_trans
						tf2.fromMsg(
							tf_buffer_
							.lookupTransform(
							base_link_frame_id_,
							odom_frame_id_,
							tf2.TimePointZero)
							.transform,
							base_link_odom_trans)

						# First, see these two references:
						# http:#wiki.ros.org/tf/Overview/Using%20Published%20Transforms#lookupTransform
						# http:#wiki.ros.org/geometry/CoordinateFrameConventions#Transform_Direction
						# We have a transform from map_frame_id_.base_link_frame_id_, but
						# it would actually transform a given pose from
						# base_link_frame_id_.map_frame_id_. We then used lookupTransform,
						# whose first two arguments are target frame and source frame, to
						# get a transform from base_link_frame_id_.odom_frame_id_.
						# However, this transform would actually transform data from
						# odom_frame_id_.base_link_frame_id_. Now imagine that we have a
						# position in the map_frame_id_ frame. First, we multiply it by the
						# inverse of the map_frame_id_.baseLinkFrameId, which will
						# transform that data from map_frame_id_ to base_link_frame_id_.
						# Now we want to go from base_link_frame_id_.odom_frame_id_, but
						# the transform we have takes data from
						# odom_frame_id_.base_link_frame_id_, so we need its inverse as
						# well. We have now transformed our data from map_frame_id_ to
						# odom_frame_id_. However, if we want other users to be able to do
						# the same, we need to broadcast the inverse of that entire
						# transform.
						map_odom_trans: Transform
						map_odom_trans.mult(world_base_link_trans, base_link_odom_trans)

						geometry_msgs.msg.TransformStamped map_odom_trans_msg
						map_odom_trans_msg.transform = tf2.toMsg(map_odom_trans)
						map_odom_trans_msg.header.stamp = static_cast<rclcpp.Time>(filtered_position.header.stamp) + tf_time_offset_
						map_odom_trans_msg.header.frame_id = map_frame_id_
						map_odom_trans_msg.child_frame_id = odom_frame_id_

						world_transform_broadcaster_.sendTransform(map_odom_trans_msg)
					except:
						self.log.Exception("Could not obtain transform from %s.%s", odom_frame_id, base_link_frame_id_)
				else:
					self.log.error("Odometry message frame_id was " << filtered_position.header.frame_id << ", expected " << map_frame_id_ << " or " << odom_frame_id_)

			# Retain the last published stamp so we can detect repeated transforms in future cycles
			self._last_published_stamp = filtered_position.header.stamp

			# Fire off the position and the transform
			if not corrected_data:
				position_pub_.publish(std.move(filtered_position))

			if self.config.print_diagnostics_:
				freq_diag_.tick()

		# Publish the acceleration if desired and filter is initialized
		if (not corrected_data) and self.config.publish_acceleration and (filtered_acceleration := self.getFilteredAccelMessage()):
			self._accel_pub.publish(filtered_acceleration)

		# Diagnostics can behave strangely when playing back from bag
		# files and using simulated time, so we have to check for
		# time suddenly moving backwards as well as the standard
		# timeout criterion before publishing.

		diag_duration = (cur_time - self._last_diag_time).nanoseconds()
		if (self.config.print_diagnostics and (diag_duration >= self.diagnostic_updater_.getPeriod().nanoseconds() or diag_duration < 0.0)):
			self._diagnostic_updater.force_update()
			self._last_diag_time = cur_time

		# Clear out expired history data
		if self.config.smooth_lagged_data:
			self._clearExpiredHistory(self._filter.last_measurement_time - self.config.history_length)

		# Warn the user if the update took too long
		loop_elapsed = (self.clock.now() - cur_time).total_seconds()
		if (loop_elapsed > 1. / self.config.update_frequency):
			self.log.error("Failed to meet update rate! Took %s seconds. "
				"Try decreasing the rate, limiting sensor output frequency, or limiting the number of "
				"sensors.", loop_elapsed)
	
	def _getFilteredOdometryMessage(self) -> Odometry | None:
		"Retrieves the EKF's output for broadcasting"
		# If the filter has received a measurement at some point...
		if not self._filter.is_initialized:
			return None
		# Grab our current state and covariance estimates
		state = self._filter.state
		estimate_error_covariance = self._filter.estimate_error_covariance

		# Convert from roll, pitch, and yaw back to quaternion for
		# orientation values
		pose = Pose3dCov(
			state[StateMembers.POSE.idxs()],
			block(estimate_error_covariance, StateMembers.POSE)
		)
		twist = Twist3dCov(
			state[StateMembers.TWIST.idxs()],
			block(estimate_error_covariance, StateMembers.TWIST),
		)
		return Odometry(
			stamp=self._filter.last_measurement_time,
			pose=pose,
			twist=twist,
		)

	def _getFilteredAccelMessage(self) -> Stamped[Acceleration3dCov] | None:
		pass

	def _clearExpiredHistory(self, cutoff_time: Timestamp):
		popped_measurements = 0
		popped_states = 0

		while (len(self._measurement_history) > 0) and self._measurement_history[0].stamp < cutoff_time:
			self._measurement_history.popleft()
			popped_measurements += 1

		while (len(self._filter_state_history) > 0) and self._filter_state_history[0].last_measurement_time < cutoff_time:
			self._filter_state_history = self._filter_state_history[1:]
			popped_states += 1

		self.log.debug("Popped %s measurements and %s states from their queues", popped_measurements, popped_states)
	
	def revert_to(self, time: Timestamp):
		self.log.debug("Requested time was %s to revert", time)

		# Walk back through the queue until we reach a filter state whose time stamp
		# is less than or equal to the requested time. Since every saved state after
		# that time will be overwritten/corrected, we can pop from the queue. If the
		# history is insufficiently short, we just take the oldest state we have.
		last_history_state = None
		while (len(self._filter_state_history) > 0) and self._filter_state_history[-1].last_measurement_time > time:
			last_history_state = self._filter_state_history.pop()

		# If the state history is not empty at this point, it means that our history
		# was large enough, and we should revert to the state at the back of the
		# history deque.
		ret_val = False
		if len(self._filter_state_history) > 0:
			ret_val = True
			last_history_state = self._filter_state_history[-1]
		else:
			self.log.debug("Insufficient history to revert to time %s", time)

			if last_history_state:
				self.log.debug("Will revert to oldest state at %s", last_history_state.latest_control_time)

		# If we have a valid reversion state, revert
		if last_history_state:
			# Reset filter to the latest state from the queue.
			state = last_history_state
			self._filter.setState(state.state_)
			self._filter.setEstimateErrorCovariance(state.estimate_error_covariance_)
			self._filter.setLastMeasurementTime(state.last_measurement_time_)

			self.log.debug("Reverted to state with time %s", state.last_measurement_time)

			# Repeat for measurements, but push every measurement onto the measurement
			# queue as we go
			restored_measurements = 0
			while self._measurement_history and self._measurement_history[-1].stamp > time:
				# Don't need to restore measurements that predate our earliest state time
				if state.last_measurement_time <= self._measurement_history[-1].stamp:
					self._measurement_queue.push(self._measurement_queue[-1])
					restored_measurements += 1

				self._measurement_history.pop()

			self.log.debug("Restored %s to measurement queue.", restored_measurements)

		return ret_val
	
	def _integrate_measurements(self, current_time: Timestamp):
		"""
		Processes all measurements in the measurement queue, in temporal order

		@param[in] current_time - The time at which to carry out integration (the
		current time)
		"""
		self.log.debug("Integration time is %s, %s measurements in queue.", current_time, len(self._measurement_queue))

		predict_to_current_time = self.config.predict_to_current_time

		# If we have any measurements in the queue, process them
		if first_measurement := self._measurement_queue.peek():
			# Check if the first measurement we're going to process is older than the
			# filter's last measurement. This means we have received an out-of-sequence
			# message (one with an old timestamp), and we need to revert both the
			# filter state and measurement queue to the first state that preceded the
			# time stamp of our first measurement.
			restored_measurement_count = 0
			if (self.config.smooth_lagged_data and first_measurement.stamp < self._filter.last_measurement_time):
				self.log.debug("Received a measurement that was %s seconds in the past. Reverting filter state and measurement queue...", (self._filter.last_measurement_time - first_measurement.stamp).total_seconds())

				original_count = len(self._measurement_queue)
				first_measurement_time = first_measurement.stamp
				first_measurement_topic = first_measurement.source.name
				# revertTo may invalidate first_measurement
				if not self.revert_to(first_measurement_time - timedelta(microseconds=1)):
					self.log.info("ERROR: history interval is too small to revert to time %s", first_measurement_time)
					# ROS_WARN_STREAM_DELAYED_THROTTLE(history_length_,
					#   "Received old measurement for topic " << first_measurement_topic <<
					#   ", but history interval is insufficiently sized. "
					#   "Measurement time is " << std::setprecision(20) <<
					#   first_measurement_time <<
					#   ", current time is " << current_time <<
					#   ", history length is " << history_length_ << ".");
					restored_measurement_count = 0
				else:
					restored_measurement_count = len(self._measurement_queue) - original_count

			while measurement := self._measurement_queue.peek():
				# If we've reached a measurement that has a time later than now, it
				# should wait until a future iteration. Since measurements are stored in
				# a priority queue, all remaining measurements will be in the future.
				if current_time < measurement.stamp:
					break
				self._measurement_queue.pop()


				# When we receive control messages, we call this directly in the control
				# callback. However, we also associate a control with each sensor message
				# so that we can support lagged smoothing. As we cannot guarantee that
				# the new control callback will fire before a new measurement, we should
				# only perform this operation if we are processing messages from the
				# history. Otherwise, we may get a new measurement, store the "old"
				# latest control, then receive a control, call setControl, and then
				# overwrite that value with this one (i.e., with the "old" control we
				# associated with the measurement).
				if self.config.use_control and restored_measurement_count > 0:
					self._filter.set_control(measurement.latest_control, measurement.latest_control_time)
					restored_measurement_count -= 1

				# This will call predict and, if necessary, correct
				self._filter.processMeasurement(measurement)

				# Store old states and measurements if we're smoothing
				if self.config.smooth_lagged_data:
					# Invariant still holds: measurementHistoryDeque_.back().time_ <
					# measurement_queue_.top().time_
					self._measurement_history.append(measurement)

					# We should only save the filter state once per unique timstamp
					if len(self._measurement_queue) == 0 or self._measurement_queue.peek().stamp != self._filter.last_measurement_time:
						self._saveFilterState(self._filter);
		elif self._filter.is_initialized:
			# In the event that we don't get any measurements for a long time,
			# we still need to continue to estimate our state. Therefore, we
			# should project the state forward here.
			last_update_delta = current_time - self._filter.last_measurement_time

			# If we get a large delta, then continuously predict until
			if last_update_delta >= self._filter.sensor_timeout:
				predict_to_current_time = True
				self.log.debug("Sensor timeout! Last measurement time was %s, current time is %s, delta is %s", self._filter.last_measurement_time, current_time, last_update_delta)
		else:
			self.log.debug("Filter not yet initialized.\n")

		if (self._filter.is_initialized and predict_to_current_time):
			last_update_delta = current_time - self._filter.last_measurement_time

			self._filter.validateDelta(last_update_delta)
			self._filter.predict(current_time, last_update_delta)

			# Update the last measurement time and last update time
			self._filter.last_measurement_time = self._filter.last_measurement_time + last_update_delta

	def _differentiate_measurements(self, current_time: Timestamp):
		"""
		Differentiate angular velocity for angular acceleration
		
		@param[in] currentTime - The time at which to carry out differentiation (the current time)
		
		Maybe more state variables can be time-differentiated to estimate higher-order states,
		but now we only focus on obtaining the angular acceleration. It implements a backward-
		Euler differentiation.
		"""
		if self._filter.is_initialized:
			dt = current_time - self._last_diff_time
			state = self._filter.state
			new_state_twist_rot = [
				state(StateMembers.Vroll),
				state(StateMembers.Vpitch),
				state(StateMembers.Vyaw)
			]
			angular_acceleration = (new_state_twist_rot - last_state_twist_rot_) / dt
			cov = self._filter.estimate_error_covariance
			for i in range(len(StateMembers.POS_ANG)):
				for j in range(len(StateMembers.POS_ANG)):
					self._angular_acceleration_cov[i, j] = cov(i + ORIENTATION_V_OFFSET, j + ORIENTATION_V_OFFSET) * 2. / ( dt * dt )
			last_state_twist_rot_ = new_state_twist_rot
			self._last_diff_time = current_time

	def _check_timestamp(self, source: DataSource, ts: Timestamp) -> bool:
		# If we've just reset the filter, then we want to ignore any messages
		# that arrive with an older timestamp
		if self._last_set_pose_ts >= ts:
			return False

		if source._last_message_time is None:
			source._last_message_time = ts
		# Make sure this message is newer than the last one
		if source._last_message_time > ts:
			# else if (reset_on_time_jump_ and rclcpp.Time.isSimTime())
			#{
			#  reset()
			#}

			# std.stringstream stream
			# stream << "The " << topic_name << " message has a timestamp before that of "
			# "the previous message received," << " this message will be ignored. This may"
			# " indicate a bad timestamp. (message time: " << msg.header.stamp.nanosec <<
			# ")"

			# addDiagnostic(
			# diagnostic_msgs.msg.DiagnosticStatus.WARN, topic_name +
			# "_timestamp", stream.str(), false)

			# self.log.debug(
			# "Message is too old. Last message time for " <<
			# 	topic_name << " is " <<
			# 	filter_utilities.toSec(last_message_times_[topic_name]) <<
			# 	", current message time is " <<
			# 	filter_utilities.toSec(msg.header.stamp) << ".\n")
			return False
		return True
	
	def prepare_pose(self, source: DataSource, msg: Stamped[Pose3dCov], update_vec: StateMembers, mode: SensorMode, imu_data: bool = False) -> Measurement | None:
		# 1. Get the measurement into a tf-friendly transform (pose) object
		tf2.Stamped<tf2.Transform> pose_tmp

		# We'll need this later for storing this measurement for differential
		# integration
		tf2.Transform cur_measurement

		# Handle issues where frame_id data is not filled out properly
		# @todo: verify that this is necessary still. New IMU handling may
		# have rendered this obsolete.
		# Otherwise, we should use our target frame
		final_target_frame = target_frame
		pose_tmp.frame_id_ = final_target_frame if (differential and not imu_data) else msg.header.frame_id

		# self.log.debug(
		# 	"Final target frame for " << topic_name << " is " <<
		# 	final_target_frame << "\n")

		pose_tmp.stamp_ = tf2.timeFromSec(
			static_cast<double>(msg.header.stamp.sec) +
			static_cast<double>(msg.header.stamp.nanosec) / 1000000000.0)

		# Fill out the position data
		pose_tmp.setOrigin(
			tf2.Vector3(
			msg.pose.pose.position.x,
			msg.pose.pose.position.y,
			msg.pose.pose.position.z))

		# Handle bad (empty) quaternions
		if False:
		# if (msg.pose.pose.orientation.x == 0 and msg.pose.pose.orientation.y == 0 and msg.pose.pose.orientation.z == 0 and msg.pose.pose.orientation.w == 0):
			orientation.setValue(0.0, 0.0, 0.0, 1.0)

			if (update_vector[StateMemberRoll] ||
			update_vector[StateMemberPitch] ||
			update_vector[StateMemberYaw])
			{
			std.stringstream stream
			stream << "The " << topic_name <<
				" message contains an invalid orientation quaternion, " <<
				"but its configuration is such that orientation data is being used."
				" Correcting..."

			addDiagnostic(
				diagnostic_msgs.msg.DiagnosticStatus.WARN,
				topic_name + "_orientation", stream.str(), false)
			}
		else:
			orientation = msg.value.value.rotation().getQuaternion()
			if np.abs(orientation.length() - 1.0) > 0.01:
				# RCLCPP_WARN_ONCE("An input was not normalized, this should NOT happen, but will normalize.")
				orientation.normalize()

		# Fill out the orientation data
		pose_tmp.setRotation(orientation)

		# 2. Get the target frame transformation
		sensor_to_robot = source.sensor_to_robot

		# handling multiple odometry origins: convert to the origin adherent to base_link.
		# make pose refer to the baseLinkFrame as source
		bool can_src_transform = false
		if (source_frame != base_link_frame_id_) {
			can_src_transform = ros_filter_utilities.lookupTransformSafe(
			tf_buffer_.get(), source_frame, base_link_frame_id_,
			rclcpp.Time(tf2.timeToSec(pose_tmp.stamp_)), tf_timeout_,
			source_frame_trans)
		}

		# 3. Make sure we can work with this data before carrying on
		if False:
			self.log.debug(
			"Could not transform measurement into " << final_target_frame <<
				". Ignoring...")
			return
		# 4. robot_localization lets users configure which variables from the
		# sensor should be fused with the filter. This is specified at the sensor
		# level. However, the data may go through transforms before being fused
		# with the state estimate. In that case, we need to know which of the
		# transformed variables came from the pre-transformed "approved" variables
		# (i.e., the ones that had "true" in their xxx_config parameter). To do
		# this, we construct matrices using the update vector values on the
		# diagonals, pass this matrix through the rotation, and use the length of
		# each row to determine the transformed update vector. The process is
		# slightly different for IMUs, as the coordinate frame transform is really
		# the base_link.imu_frame transform, and not a transform from some other
		# world-fixed frame (even though the IMU data itself *is* reported in a
		# world fixed frame).
		mask_position = mask(StateMembers.POS_LIN)
		mask_orientation = mask(StateMembers.POS_ANG)

		if imu_data:
			# We have to treat IMU orientation data differently. Even though we are
			# dealing with pose data when we work with orientations, for IMUs, the
			# frame_id is the frame in which the sensor is mounted, and not the
			# coordinate frame of the IMU. Imagine an IMU that is mounted facing
			# sideways. The pitch in the IMU frame becomes roll for the vehicle. This
			# means that we need to rotate roll and pitch angles by the IMU's
			# mounting yaw offset, and we must apply similar treatment to its update
			# mask and covariance.
			double dummy, yaw
			target_frame_trans.getBasis().getRPY(dummy, dummy, yaw)
			tf2.Matrix3x3 trans_tmp
			trans_tmp.setRPY(0.0, 0.0, yaw)

			mask_position = trans_tmp * mask_position
			mask_orientation = trans_tmp * mask_orientation
		else:
			mask_position = target_frame_trans.getBasis() * mask_position
			mask_orientation = target_frame_trans.getBasis() * mask_orientation

		# Now copy the mask values back into the update vector: any row with a
		# significant vector length indicates that we want to set that variable to
		# true in the update vector.
		update_vector[StateMemberX] = static_cast<int>(
		mask_position.getRow(StateMemberX - POSITION_OFFSET).length() >= 1e-6)
		update_vector[StateMemberY] = static_cast<int>(
		mask_position.getRow(StateMemberY - POSITION_OFFSET).length() >= 1e-6)
		update_vector[StateMemberZ] = static_cast<int>(
		mask_position.getRow(StateMemberZ - POSITION_OFFSET).length() >= 1e-6)
		update_vector[StateMemberRoll] = static_cast<int>(
		mask_orientation.getRow(StateMemberRoll - ORIENTATION_OFFSET)
		.length() >= 1e-6)
		update_vector[StateMemberPitch] = static_cast<int>(
		mask_orientation.getRow(StateMemberPitch - ORIENTATION_OFFSET)
		.length() >= 1e-6)
		update_vector[StateMemberYaw] = static_cast<int>(
		mask_orientation.getRow(StateMemberYaw - ORIENTATION_OFFSET).length() >=
		1e-6)

		# 5a. We'll need to rotate the covariance as well. Create a container and
		# copy over the covariance data
		Eigen.MatrixXd covariance(POSE_SIZE, POSE_SIZE)
		covariance.setZero()
		copyCovariance(
		&(msg.pose.covariance[0]), covariance, topic_name,
		update_vector, POSITION_OFFSET, POSE_SIZE)

		# 5b. Now rotate the covariance: create an augmented matrix that
		# contains a 3D rotation matrix in the upper-left and lower-right
		# quadrants, with zeros elsewhere.
		tf2.Matrix3x3 rot
		Eigen.MatrixXd rot6d(POSE_SIZE, POSE_SIZE)
		rot6d.setIdentity()
		Eigen.MatrixXd covariance_rotated

		# Transform pose covariance due to a different pose source origin
		if can_src_transform:
			rot6d = rot3_to_mat6(source_frame_trans.rotation())
			# (source_frame != base_link_frame_id_) already satisfied
			rot.setRotation(source_frame_trans.getRotation())
			for (size_t r_ind = 0 r_ind < POSITION_SIZE ++r_ind) {
				# let's borrow rot6d here...
				rot6d(r_ind, 0) = rot.getRow(r_ind).getX()
				rot6d(r_ind, 1) = rot.getRow(r_ind).getY()
				rot6d(r_ind, 2) = rot.getRow(r_ind).getZ()
				rot6d(r_ind + POSITION_SIZE, 3) = rot.getRow(r_ind).getX()
				rot6d(r_ind + POSITION_SIZE, 4) = rot.getRow(r_ind).getY()
				rot6d(r_ind + POSITION_SIZE, 5) = rot.getRow(r_ind).getZ()
			}
			# since the transformation is a post-multiply
			covariance = rot6d.transpose() * covariance.eval() * rot6d
		}
		# return rot6d to its initial state.
		rot6d.setIdentity()

		if imu_data:
			# Apply the same special logic to the IMU covariance rotation
			double dummy, yaw
			target_frame_trans.getBasis().getRPY(dummy, dummy, yaw)
			rot.setRPY(0.0, 0.0, yaw)
		else:
			rot.setRotation(target_frame_trans.getRotation())

		rot6d = rot_to_mat6(rot)

		# Now carry out the rotation
		covariance_rotated = rot6d * covariance * rot6d.transpose()

		self.log.debug("After rotating into the robot frame, covariance is %s", covariance_rotated)

		# 6a. For IMU data, the transform that we get is the transform from the
		# body frame of the robot (e.g., base_link) to the mounting frame of the
		# robot. It is *not* the coordinate frame in which the IMU orientation data
		# is reported. If the IMU is mounted in a non-neutral orientation, we need
		# to remove those offsets, and then we need to potentially "swap" roll and
		# pitch. Note that this transform does NOT handle NED.ENU conversions.
		# Data is assumed to be in the ENU frame when it is received.
		if imu_data:
			# First, convert the transform and measurement rotation to RPY
			# @todo: There must be a way to handle this with quaternions. Need to
			# look into it.
			double roll_offset = 0
			double pitch_offset = 0
			double yaw_offset = 0
			double roll = 0
			double pitch = 0
			double yaw = 0
			ros_filter_utilities.quatToRPY(
				target_frame_trans.getRotation(),
				roll_offset, pitch_offset, yaw_offset)
			ros_filter_utilities.quatToRPY(pose_tmp.getRotation(), roll, pitch, yaw)

			# 6b. Apply the offset (making sure to bound them), and throw them in a
			# vector
			tf2.Vector3 rpy_angles(
				angles.normalize_angle(roll - roll_offset),
				angles.normalize_angle(pitch - pitch_offset),
				angles.normalize_angle(yaw - yaw_offset))

			# 6c. Now we need to rotate the roll and pitch by the yaw offset value.
			# Imagine a case where an IMU is mounted facing sideways. In that case
			# pitch for the IMU's world frame is roll for the robot.
			tf2.Matrix3x3 mat
			mat.setRPY(0.0, 0.0, yaw_offset)
			rpy_angles = mat * rpy_angles
			pose_tmp.getBasis().setRPY(
				rpy_angles.getX(), rpy_angles.getY(),
				rpy_angles.getZ())

			# We will use this target transformation later on, but
			# we've already transformed this data as if the IMU
			# were mounted neutrall on the robot, so we can just
			# make the transform the identity.
			target_frame_trans.setIdentity()

		# 7. Two cases: if we're in differential mode, we need to generate a twist
		# message. Otherwise, we just transform it to the target frame.
		if mode == SensorMode.DIFFERENTIAL:
			success = False

			# We're going to be playing with pose_tmp, so store it,
			# as we'll need to save its current value for the next
			# measurement.
			cur_measurement = pose_tmp

			# Make sure we have previous measurements to work with
			if (previous_measurements_.count(topic_name) > 0 and previous_measurement_covariances_.count(topic_name) > 0):
				# 7a. If we are carrying out differential integration and
				# we have a previous measurement for this sensor,then we
				# need to apply the inverse of that measurement to this new
				# measurement to produce a "delta" measurement between the two.
				# Even if we're not using all of the variables from this sensor,
				# we need to use the whole measurement to determine the delta
				# to the new measurement
				tf2.Transform prev_measurement = previous_measurements_[topic_name]
				pose_tmp.setData(prev_measurement.inverseTimes(pose_tmp))

				self.log.debug(
				"Previous measurement:\n" <<
					previous_measurements_[topic_name] <<
					"\nAfter removing previous measurement, measurement delta is:\n" <<
					pose_tmp << "\n")

				# 7b. Now we we have a measurement delta in the frame_id of the
				# message, but we want that delta to be in the target frame, so
				# we need to apply the rotation of the target frame transform.
				target_frame_trans.setOrigin(tf2.Vector3(0.0, 0.0, 0.0))
				pose_tmp.mult(target_frame_trans, pose_tmp)

				self.log.debug(
				"After rotating to the target frame, measurement delta is:\n" <<
					pose_tmp << "\n")

				# 7c. Now use the time difference from the last message to compute
				# translational and rotational velocities
				double dt = filter_utilities.toSec(msg.header.stamp) -
				filter_utilities.toSec(last_message_times_[topic_name])
				double xVel = pose_tmp.getOrigin().getX() / dt
				double yVel = pose_tmp.getOrigin().getY() / dt
				double zVel = pose_tmp.getOrigin().getZ() / dt

				double rollVel = 0
				double pitchVel = 0
				double yawVel = 0

				ros_filter_utilities.quatToRPY(
				pose_tmp.getRotation(), rollVel,
				pitchVel, yawVel)
				rollVel /= dt
				pitchVel /= dt
				yawVel /= dt

				self.log.debug(
				"Previous message time was " <<
					filter_utilities.toSec(last_message_times_[topic_name]) <<
					", current message time is " <<
					filter_utilities.toSec(msg.header.stamp) << ", delta is " <<
					dt << ", velocity is (vX, vY, vZ): (" << xVel << ", " <<
					yVel << ", " << zVel << ")\n" <<
					"(vRoll, vPitch, vYaw): (" << rollVel << ", " << pitchVel <<
					", " << yawVel << ")\n")

				# 7d. Fill out the velocity data in the message
				twist_ptr = Twist3dCov(
					Twist3d(
						xVel,
						yVel,
						zVel,
						rollVel,
						pitchVel,
						yawVel,
					),
				)
				std.vector<bool> twist_update_vec(STATE_SIZE, false)
				std.copy(
				update_vector.begin() + POSITION_OFFSET,
				update_vector.begin() + POSE_SIZE,
				twist_update_vec.begin() + POSITION_V_OFFSET)
				std.copy(
				twist_update_vec.begin(), twist_update_vec.end(),
				update_vector.begin())

				# 7e. Now rotate the previous covariance for this measurement to get it
				# into the target frame, and add the current measurement's rotated
				# covariance to the previous measurement's rotated covariance, and
				# multiply by the time delta.
				prev_covar_rotated = rot6d @ source.previous_measurement.covariance @ rot6d.transpose()
				covariance_rotated =
				(covariance_rotated.eval() + prev_covar_rotated) * dt
				copyCovariance(
				covariance_rotated, &(twist_ptr.twist.covariance[0]),
				POSE_SIZE)

				self.log.debug(
				"Previous measurement covariance:\n" <<
					previous_measurement_covariances_[topic_name] <<
					"\nPrevious measurement covariance rotated:\n" <<
					prev_covar_rotated << "\nFinal twist covariance:\n" <<
					covariance_rotated << "\n")

				# Now pass this on to prepareTwist, which will convert it to the
				# required frame
				m = self.prepare_twist()
				success = prepareTwist(
				twist_ptr, topic_name + "_twist",
				base_link_frame_id_, update_vector,
				measurement, measurement_covariance)
			}

			# 7f. Update the previous measurement and measurement covariance
			previous_measurements_[topic_name] = cur_measurement
			previous_measurement_covariances_[topic_name] = covariance

			retVal = success
		else:
			# make pose refer to the baseLinkFrame as source
			# can_src_transform == true => ( sourceFrame != baseLinkFrameId_ )
			if (can_src_transform) {
				pose_tmp.setData(pose_tmp * source_frame_trans)
			}

			# 7g. If we're in relative mode, remove the initial measurement
			if (relative) {
				if (initial_measurements_.count(topic_name) == 0) {
				initial_measurements_.insert(
					std.pair<std.string, tf2.Transform>(topic_name, pose_tmp))
				}

				tf2.Transform initial_measurement = initial_measurements_[topic_name]
				pose_tmp.setData(initial_measurement.inverseTimes(pose_tmp))
			}

			# 7h. Apply the target frame transformation to the pose object.
			pose_tmp.mult(target_frame_trans, pose_tmp)
			pose_tmp.frame_id_ = final_target_frame

			# 7i. Finally, copy everything into our measurement and covariance
			# objects
			measurement(StateMemberX) = pose_tmp.getOrigin().x()
			measurement(StateMemberY) = pose_tmp.getOrigin().y()
			measurement(StateMemberZ) = pose_tmp.getOrigin().z()

			# The filter needs roll, pitch, and yaw values instead of quaternions
			double roll, pitch, yaw
			ros_filter_utilities.quatToRPY(pose_tmp.getRotation(), roll, pitch, yaw)
			measurement(StateMemberRoll) = roll
			measurement(StateMemberPitch) = pitch
			measurement(StateMemberYaw) = yaw

			measurement_covariance.block(0, 0, POSE_SIZE, POSE_SIZE) =
				covariance_rotated.block(0, 0, POSE_SIZE, POSE_SIZE)

			# 8. Handle 2D mode
			if self.config.force_2d:
				self.forceTwoD(measurement, measurement_covariance, update_vector)

			retVal = true
		return retVal

	def prepare_twist(self, source: DataSource, twist: Twist3dCov, update_vector: StateMembers, ts: Timestamp) -> Measurement:
		# 1. Get the measurement into two separate vector objects.
		twist_lin = np.array([twist.twist.dx, twist.twist.dy, twist.twist.dz])
		twist_rot = np.array([twist.twist.rx, twist.twist.ry, twist.twist.rz])

		# 1a. This sensor may or may not measure rotational velocity. Regardless,
		# if it measures linear velocity, then later on, we'll need to remove "false"
		# linear velocity resulting from angular velocity and the translational
		# offset of the sensor from the vehicle origin.
		state = self._filter.state
		state_twist_rot = state[StateMembers.VEL_ANG.idxs()]

		# 2. robot_localization lets users configure which variables from the sensor
		# should be
		#    fused with the filter. This is specified at the sensor level. However,
		#    the data may go through transforms before being fused with the state
		#    estimate. In that case, we need to know which of the transformed
		#    variables came from the pre-transformed "approved" variables (i.e., the
		#    ones that had "true" in their xxx_config parameter). To do this, we
		#    construct matrices using the update vector values on the diagonals, pass
		#    this matrix through the rotation, and use the length of each row to
		#    determine the transformed update vector.
		
		maskLin = mask(update_vector, StateMembers.VEL_LIN)
		maskRot = mask(update_vector, StateMembers.VEL_ANG)

		# 3. We'll need to rotate the covariance as well
		covariance_rotated = np.zeros((len(StateMembers.TWIST), len(StateMembers.TWIST)), dtype=float)
		copyCovariance(
			&(msg.twist.covariance[0]), covariance_rotated, topic_name,
			update_vector, POSITION_V_OFFSET, TWIST_SIZE)

		# self.log.debug(
		# 	"Original measurement as tf object:\nLinear: " <<
		# 	twist_lin << "Rotational: " << meas_twist_rot <<
		# 	"\nOriginal update vector:\n" <<
		# 	update_vector << "\nOriginal covariance matrix:\n" <<
		# 	covariance_rotated << "\n")

		# 4. We need to transform this into the target frame (probably base_link)
		sensor_to_robot = source.robot_to_sensor.inverse()

		# Transform to correct frame. Note that we can get linear velocity
		# as a result of the sensor offset and rotational velocity
		meas_twist_rot = target_frame_trans.getBasis() * meas_twist_rot
		twist_lin = target_frame_trans.getBasis() * twist_lin + target_frame_trans.getOrigin().cross(state_twist_rot)
		maskLin = target_frame_trans.getBasis() * maskLin
		maskRot = target_frame_trans.getBasis() * maskRot

		# Now copy the mask values back into the update vector
		update_vector[StateMemberVx] = static_cast<int>(
		maskLin.getRow(StateMemberVx - POSITION_V_OFFSET).length() >= 1e-6)
		update_vector[StateMemberVy] = static_cast<int>(
		maskLin.getRow(StateMemberVy - POSITION_V_OFFSET).length() >= 1e-6)
		update_vector[StateMemberVz] = static_cast<int>(
		maskLin.getRow(StateMemberVz - POSITION_V_OFFSET).length() >= 1e-6)
		update_vector[StateMemberVroll] = static_cast<int>(
		maskRot.getRow(StateMemberVroll - ORIENTATION_V_OFFSET).length() >=
		1e-6)
		update_vector[StateMemberVpitch] = static_cast<int>(
		maskRot.getRow(StateMemberVpitch - ORIENTATION_V_OFFSET).length() >=
		1e-6)
		update_vector[StateMemberVyaw] = static_cast<int>(
		maskRot.getRow(StateMemberVyaw - ORIENTATION_V_OFFSET).length() >=
		1e-6)

		# self.log.debug(
		# msg.header.frame_id <<
		# 	"." << target_frame << " transform:\n" <<
		# 	target_frame_trans << "\nAfter applying transform to " <<
		# 	target_frame << ", update vector is:\n" <<
		# 	update_vector << "\nAfter applying transform to " <<
		# 	target_frame << ", measurement is:\n" <<
		# 	"Linear: " << twist_lin << "Rotational: " << meas_twist_rot <<
		# 	"\n")

		# 5. Now rotate the covariance: create an augmented
		# matrix that contains a 3D rotation matrix in the
		# upper-left and lower-right quadrants, and zeros
		# elsewhere
		rot6d = rot_to_mat6(sensor_to_robot.rotation)
		

		# Carry out the rotation
		covariance_rotated = rot6d @ covariance_rotated @ rot6d.T

		self.log.debug("Transformed covariance is %s", covariance_rotated)

		# 6. Store our corrected measurement and covariance
		measurement = Measurement(ts, source)
		measurement.measure(StateMembers.VEL_LIN, twist_lin)
		measurement.measure(StateMembers.VEL_ANG, twist_rot)

		# Copy the covariances
		measurement.copy_covariance(StateMembers.TWIST, covariance_rotated)

		# 7. Handle 2D mode
		if (self.config.force_2d):
			self.forceTwoD(measurement)
		return measurement
	
	def forceTwoD(self, measurement: Measurement):
		m3 = StateMembers.Z | StateMembers.Roll | StateMembers.Pitch | StateMembers.Vz | StateMembers.Vroll | StateMembers.Vpitch | StateMembers.Az
		measurement[m3] = 0.0
		for m in m3:
			mi = m.idx()
			measurement.measurement[mi] = 0.0
			measurement.covariance[mi, mi] = 1e-6
		measurement.update_vector |= m3
	
	def handle_acceleration(self, source: DataSource, accel: Acceleration3dCov, ts: Timestamp):
		if not self._check_timestamp(source, ts):
			return
		
		self.log.debug("Update vector for %s is:", source.name)
		measurement = Measurement(ts, source)

		# Make sure we're actually updating at least one of these variables
		update_vector_corrected = callback_data.update_vector_

		# Prepare the twist data for inclusion in the filter
		if (self.prepareAcceleration(source, accel, ts)
			msg, topic_name, target_frame, callback_data.relative_,
			update_vector_corrected, measurement,
			measurement_covariance)):
			# Store the measurement. Add an "acceleration" suffix so we know what
			# kind of measurement we're dealing with when we debug the core filter
			# logic.
			enqueueMeasurement(
				topic_name, measurement, measurement_covariance,
				update_vector_corrected,
				callback_data.rejection_threshold_, msg.header.stamp)

			self.log.debug(
				"Enqueued new measurement for " << topic_name <<
				"_acceleration\n")
		else:
			self.log.debug(
				"Did *not* enqueue measurement for " << topic_name <<
				"_acceleration\n")

		last_message_times_[topic_name] = msg.header.stamp
	
	def handle_twist(self, update_vector: StateMembers, rejection_threshold: float, source: DataSource, twist: Twist3dCov, ts: Timestamp):
		if not self._check_timestamp(source, ts):
			return
		self.log.debug("Update vector for %s is: %s", source)

		# Prepare the twist data for inclusion in the filter
		if measurement := self.prepare_twist(source, twist, update_vector, ts):
			# Store the measurement. Add a "twist" suffix so we know what kind of
			# measurement we're dealing with when we debug the core filter logic.
			self._enqueue_measurement(measurement, rejection_threshold)

			# self.log.debug("Enqueued new measurement for " << topic_name << "_twist\n")
		else:
			self.log.debug("Did *not* enqueue measurement for %s_twist", source.name)

		source._last_message_time = ts

		self.log.debug("Last message time for %s is now %s", source.name, ts.as_seconds())
	
	def handle_pose(self, update_vector: StateMembers, rejection_threshold: float, source: DataSource, pose: Pose3dCov, ts: Timestamp, mode: SensorMode):
		if not self._check_timestamp(source, ts):
			return

		# Prepare the pose data for inclusion in the filter
		if measurement := self.prepare_pose(source, Stamped(pose, ts), update_vector, mode):
			# Store the measurement. Add a "pose" suffix so we know what kind of
			# measurement we're dealing with when we debug the core filter logic.
			self._enqueue_measurement(measurement, rejection_threshold)
			self.log.debug("Enqueued new measurement for %s", source.name);
		else:
			self.log.debug("Did *not* enqueue new measurement for %s", source.name);

		# RF_DEBUG(
		# "Last message time for " <<
		# 	topic_name << " is now " <<
		# 	filter_utilities::toSec(last_message_times_[topic_name]) <<
		# 	"\n");
		source.last_message_time = ts

	def _enqueue_measurement(self, measurement: Measurement, rejection_threshold: float):
		meas = MeasurementPtr(new Measurement())

		meas.topic_name_ = topic_name
		meas.measurement_ = measurement
		meas.covariance_ = measurement_covariance
		meas.update_vector_ = update_vector
		meas.time_ = time
		meas.mahalanobis_thresh_ = mahalanobis_thresh
		meas.latest_control_ = latest_control_
		meas.latest_control_time_ = latest_control_time_
		measurement_queue_.push(meas)
	
	def reset(self):
		# Get rid of any initial poses (pretend we've never had a measurement)
		initial_measurements_.clear()
		previous_measurements_.clear()
		previous_measurement_covariances_.clear()

		self._measurement_queue.clear()
		self._filter_state_history.clear()
		self._measurement_history.clear()

		# Also set the last set pose time, so we ignore all messages
		# that occur before it
		self._last_set_pose_time = Timestamp.invalid(self.clock)
		self._last_diag_time = Timestamp.invalid(self.clock)
		self._latest_control_time = Timestamp.invalid(self.clock)
		self._last_published_stamp = Timestamp.invalid(self.clock)

		# clear tf buffer to avoid TF_OLD_DATA errors
		tf_buffer_.clear()

		# clear last message timestamp, so older messages will be accepted
		last_message_times_.clear()

		# reset filter to uninitialized state
		self._filter.reset()

		# Restore filter parameters that we got from the ROS parameter server
		self._filter.setSensorTimeout(sensor_timeout_)
		self._filter.setProcessNoiseCovariance(process_noise_covariance_)
		self._filter.setEstimateErrorCovariance(initial_estimate_error_covariance_)
