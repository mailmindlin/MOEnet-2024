from typing import Literal, Generic, TypeVar
import logging
from functools import reduce
from enum import Enum, auto
from datetime import timedelta

from pydantic import BaseModel, Field
import numpy as np
from wpiutil.log import DataLog

from typedef.cfg import PoseEstimatorConfig1
from typedef.geom import Transform3d, Rotation3d, Pose3d, Twist3d, Quaternion, Translation3d
from typedef.geom_cov import (
	Acceleration3dCov, Acceleration3d,
	AngularAcceleration3d,
    LinearAcceleration3dCov, LinearAcceleration3d,
    Twist3dCov, Pose3dCov,
    Odometry,
    rot3_to_mat, rot3_to_mat6, rot3_flatten
)
from util.timestamp import Timestamp, Stamped
from util.clock import WallClock, Clock
from .base import ControlMembers, StateMembers, Measurement, block
from .ekf import EKF
from ..util.replay import ReplayFilter

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

T = TypeVar('T')
class DataSource(Generic[T]):
	name: str
	robot_to_sensor: Transform3d
	initial_measurement: T | None
	remove_gravitational_acceleration: bool = False
	last_message_time: Timestamp | None = None

	def __init__(self, estimator: 'PoseEstimator', name: str, robot_to_sensor: Transform3d) -> None:
		self.initial_measurement = None
		self.last_message_time = None
		self.estimator = estimator
		self.name = name
		self.robot_to_sensor = robot_to_sensor
		self.previous_measurement: T | None = None
	
	@property
	def sensor_to_robot(self) -> Transform3d:
		return self.robot_to_sensor.inverse()
	
	def measure(self, msg: T):
		"Record a measurement"
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
			msg.stamp,
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
			msg.stamp,
		)

class IMUSource(DataSource[Stamped[Twist3dCov]]):
	def __init__(self, estimator: 'PoseEstimator', name: str, robot_to_sensor: Transform3d, pose_threshold: float | None, twist_threshold: float | None, linac_threshold: float | None, remove_gravity: bool, mode: SensorMode):
		super().__init__(estimator, name, robot_to_sensor)
		self.pose_threshold = pose_threshold
		self.twist_threshold = twist_threshold
		self.mode = mode


# Utility functions
def mask_to_mat(members: StateMembers, mask: StateMembers) -> np.ndarray[float, tuple[Literal[3], Literal[3]]]:
	assert len(mask) == 3
	res = np.zeros((3, 3), dtype=np.float32)
	for i, v in enumerate(mask):
		res[i,i] = 1 if (members & v) else 0
	return res

def mat_to_mask(mat: np.ndarray[float, tuple[Literal[3], Literal[3]]], mask: StateMembers) -> StateMembers:
	assert len(mask) == 3
	res = StateMembers.NONE
	for i, v in enumerate(mask):
		if np.linalg.norm(mat[i,:]) > 1e-6:
			res |= v
	return res

def update_mask_rotation(prev: StateMembers, rotation: Rotation3d, masks: StateMembers) -> StateMembers:
	mats = [
		mask_to_mat(prev, mask)
		for mask in masks
	]

	rot_mat = rot3_to_mat(rotation)
	mat_lin = rot_mat @ mat_lin
	mat_rot = rot_mat @ mat_rot

	prev_cleared = StateMembers(prev)
	for mat, mask in zip(mats, masks):
		prev_cleared = (prev_cleared & (~mask)) | mat_to_mask(mat, mask)
	return prev_cleared


class PoseEstimator:
	"""
	Kalman filter based on robot_localization
	"""
	def __init__(self, config: PoseEstimatorConfig1, clock: Clock, log: logging.Logger, datalog: DataLog | None):
		self._sources: list[DataSource] = list()
		self.log = log
		self.datalog = datalog
		self.config = config
		self.clock = clock
		self._filter = EKF(
			self.log.getChild('ekf'),
			self.clock,
		)

		self._last_set_pose_ts = Timestamp.invalid()
		self._last_diag_time = self.clock.now()
		self._last_diff_time = Timestamp.invalid(self.clock)

		self._sources: list[DataSource] = list()
		self._replay = ReplayFilter(
			self.log,
			self._filter,
		)
		
		self.twist_var_counts = {
			key: 0
			for key in StateMembers.TWIST
		}
		self.abs_pose_var_counts = {
			key: 0
			for key in StateMembers.POSE
		}
	
	def initialize(self):
		# Init the last measurement time so we don't get a huge initial delta
		self._filter.last_measurement_ts = self.clock.now()
		
	def set_pose(self, msg: Stamped[Pose3d | Pose3dCov]):
		# RCLCPP_INFO_STREAM(
		# 	get_logger(),
		# 	"Received set_pose request with value\n" << geometry_msgs.msg.to_yaml(*msg))

		# Get rid of any initial poses (pretend we've never had a measurement)
		for source in self._sources:
			source.initial_measurement = None
			source.previous_measurement = None
		
		self._replay.clear()

		# Also set the last set pose time, so we ignore all messages
		# that occur before it

		self._last_set_pose_ts = msg.stamp

		# Set the state vector to the reported pose
		ALL = reduce(lambda a, b: a|b, StateMembers)
		measurement = Measurement(msg.stamp, None, update_vector=ALL)
		# We only measure pose variables, so initialize the vector to 0
		measurement.measure(ALL, 0.0, 1e-6)

		# Prepare the pose data (really just using this to transform it into the
		# target frame). Twist data is going to get zeroed out.
		# Since pose messages do not provide a child_frame_id, it defaults to baseLinkFrameId_
		measurement: Measurement = self.prepare_pose(None, msg, SensorMode.ABSOLUTE)
		assert measurement

		# For the state
		self._filter.state = measurement.mean_dense
		self._filter.estimate_error_covariance = measurement.covariance_dense

		self._filter.last_measurement_ts = self.clock.now()

	def make_odom(self, name: str, robot_to_sensor: Transform3d, update: StateMembers, pose_threshold: float | None = None, twist_threshold: float | None = None, mode: SensorMode = SensorMode.ABSOLUTE) -> DataSource[Odometry]:
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
	
	def sample_pose(self, ts: Timestamp) -> Pose3d:
		pass

	def poll(self):
		now = self.clock.now()
		self._replay.poll(now)

		if self._toggled_on:
			# Now we'll integrate any measurements we've received if requested,
			# and update angular acceleration.
			self._integrate_measurements(now)
			self._differentiate_measurements(now)
		else:
			# Clear out measurements since we're not currently processing new entries
			self._measurement_queue.clear()

			# Reset last measurement time so we don't get a large time delta on toggle
			if self._filter.is_initialized:
				self._filter.last_measurement_ts = self.clock.now()

		# Get latest state and publish it
		corrected_data = False
		if filtered_position := self._get_filtered_odometry():
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
			if not filtered_position.isfinite():
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
				# if filtered_position.header.frame_id == odom_frame_id_:
				# 	world_transform_broadcaster_.sendTransform(world_base_link_trans_msg_)
				# elif (filtered_position.header.frame_id == map_frame_id_):
				# 	try:
				# 		tf2.Transform world_base_link_trans
				# 		tf2.fromMsg(
				# 			world_base_link_trans_msg_.transform,
				# 			world_base_link_trans)

				# 		tf2.Transform base_link_odom_trans
				# 		tf2.fromMsg(
				# 			tf_buffer_
				# 			.lookupTransform(
				# 			base_link_frame_id_,
				# 			odom_frame_id_,
				# 			tf2.TimePointZero)
				# 			.transform,
				# 			base_link_odom_trans)

				# 		# First, see these two references:
				# 		# http:#wiki.ros.org/tf/Overview/Using%20Published%20Transforms#lookupTransform
				# 		# http:#wiki.ros.org/geometry/CoordinateFrameConventions#Transform_Direction
				# 		# We have a transform from map_frame_id_.base_link_frame_id_, but
				# 		# it would actually transform a given pose from
				# 		# base_link_frame_id_.map_frame_id_. We then used lookupTransform,
				# 		# whose first two arguments are target frame and source frame, to
				# 		# get a transform from base_link_frame_id_.odom_frame_id_.
				# 		# However, this transform would actually transform data from
				# 		# odom_frame_id_.base_link_frame_id_. Now imagine that we have a
				# 		# position in the map_frame_id_ frame. First, we multiply it by the
				# 		# inverse of the map_frame_id_.baseLinkFrameId, which will
				# 		# transform that data from map_frame_id_ to base_link_frame_id_.
				# 		# Now we want to go from base_link_frame_id_.odom_frame_id_, but
				# 		# the transform we have takes data from
				# 		# odom_frame_id_.base_link_frame_id_, so we need its inverse as
				# 		# well. We have now transformed our data from map_frame_id_ to
				# 		# odom_frame_id_. However, if we want other users to be able to do
				# 		# the same, we need to broadcast the inverse of that entire
				# 		# transform.
				# 		map_odom_trans: Transform
				# 		map_odom_trans.mult(world_base_link_trans, base_link_odom_trans)

				# 		geometry_msgs.msg.TransformStamped map_odom_trans_msg
				# 		map_odom_trans_msg.transform = tf2.toMsg(map_odom_trans)
				# 		map_odom_trans_msg.header.stamp = static_cast<rclcpp.Time>(filtered_position.header.stamp) + tf_time_offset_
				# 		map_odom_trans_msg.header.frame_id = map_frame_id_
				# 		map_odom_trans_msg.child_frame_id = odom_frame_id_

				# 		world_transform_broadcaster_.sendTransform(map_odom_trans_msg)
				# 	except:
				# 		self.log.exception("Could not obtain transform from %s.%s", odom_frame_id, base_link_frame_id_)
				# else:
				# 	self.log.error("Odometry message frame_id was " << filtered_position.header.frame_id << ", expected " << map_frame_id_ << " or " << odom_frame_id_)
				pass

			# Retain the last published stamp so we can detect repeated transforms in future cycles
			self._last_published_stamp = filtered_position.header.stamp

			# Fire off the position and the transform
			if not corrected_data:
				position_pub_.publish(filtered_position)

			if self.config.print_diagnostics:
				self._freq_diag.tick()

		# Publish the acceleration if desired and filter is initialized
		if (not corrected_data) and self.config.publish_acceleration and (filtered_acceleration := self._get_filtered_acceleration()):
			self._accel_pub.publish(filtered_acceleration)

		# Diagnostics can behave strangely when playing back from bag
		# files and using simulated time, so we have to check for
		# time suddenly moving backwards as well as the standard
		# timeout criterion before publishing.

		diag_duration = (now - self._last_diag_time).nanoseconds()
		if (self.config.print_diagnostics and (diag_duration >= self.diagnostic_updater_.getPeriod().nanoseconds() or diag_duration < 0.0)):
			self._diagnostic_updater.force_update()
			self._last_diag_time = now

		# Clear out expired history data
		if self.config.smooth_lagged_data:
			self._replay._clear_expired_history(self._filter.last_measurement_ts - self.config.history_length)

		# Warn the user if the update took too long
		loop_elapsed = (self.clock.now() - now).total_seconds()
		if (loop_elapsed > 1. / self.config.update_frequency):
			self.log.error("Failed to meet update rate! Took %s seconds. "
				"Try decreasing the rate, limiting sensor output frequency, or limiting the number of "
				"sensors.", loop_elapsed)
	
	def _get_filtered_odometry(self) -> Odometry | None:
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
			stamp=self._filter.last_measurement_ts,
			pose=pose,
			twist=twist,
		)

	def _get_filtered_acceleration(self) -> Stamped[Acceleration3dCov] | None:
		# If the filter has received a measurement at some point...
		if not self._filter.is_initialized:
			return None
		# Grab our current state and covariance estimates
		state = self._filter.state
		estimate_error_covariance = self._filter.estimate_error_covariance

		# Fill out the accel_msg
		msg = Acceleration3dCov(
			Acceleration3d(
				LinearAcceleration3d(*state[StateMembers.ACC_LIN.idxs()]),
				AngularAcceleration3d(self._angular_acceleration)
			),

		)

		# Fill the covariance (only the left-upper matrix since we are not
		# estimating the rotational accelerations arround the axes
		for i in range(ACCELERATION_SIZE):
			for j in range(ACCELERATION_SIZE):
				# We use the POSE_SIZE since the accel cov matrix of ROS is 6x6
				message.accel.covariance[POSE_SIZE * i + j] = estimate_error_covariance(
				i + POSITION_A_OFFSET, j + POSITION_A_OFFSET);
		for i in range(ACCELERATION_SIZE, POSE_SIZE):
			for j in range(ACCELERATION_SIZE, POSE_SIZE):
				# fill out the angular portion. We assume the linear and angular portions are independent.
				message.accel.covariance[POSE_SIZE * i + j] = angular_acceleration_cov_[i - ACCELERATION_SIZE, j - ACCELERATION_SIZE]

		# Fill header information
		return Stamped(
			msg,
			self._filter.last_measurement_ts
		)

	def revert_to(self, time: Timestamp):
		self.log.debug("Requested time was %s to revert", time)
		return self._replay.revert_to(time)

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
	
	def _prepare_pose_differential(self, source: DataSource[Stamped[Pose3dCov]], pose: Stamped[Pose3dCov], update_vector: StateMembers):
		# Make sure we have previous measurements to work with
		prev_measurement = source.previous_measurement
		if prev_measurement is not None:
			# 7a. If we are carrying out differential integration and
			# we have a previous measurement for this sensor,then we
			# need to apply the inverse of that measurement to this new
			# measurement to produce a "delta" measurement between the two.
			# Even if we're not using all of the variables from this sensor,
			# we need to use the whole measurement to determine the delta
			# to the new measurement
			delta = pose.value.mean.relativeTo(prev_measurement.value.mean)

			self.log.debug("Previous measurement: %s", prev_measurement)
			self.log.debug("After removing previous measurement, measurement delta is:%s", pose)

			# 7b. Now we we have a measurement delta in the frame_id of the
			# message, but we want that delta to be in the target frame, so
			# we need to apply the rotation of the target frame transform.
			sensor_to_robot = Transform3d(
				source.sensor_to_robot.rotation(),
				Translation3d(),
			)
			delta = delta.transformBy(sensor_to_robot)
			self.log.debug("After rotating to the target frame, measurement delta is: %s", pose)

			# 7c. Now use the time difference from the last message to compute
			# translational and rotational velocities
			dt = (pose.stamp - prev_measurement.stamp).total_seconds()
			linVel = delta.translation() / dt
			angVel = delta.rotation() / dt

			self.log.debug("Previous message time was %s, current message time is %s, delta is %s, velocity is (vX, vY, vZ): (%s, %s, %s)",
				source.last_message_time,
				pose.stamp,
				dt,
				xVel, yVel, zVel
			)
			self.log.debug("(vRoll, vPitch, vYaw): (%s, %s, %s)", rollVel, pitchVel, yawVel)

			# 7d. Fill out the velocity data in the message
			twist = Twist3dCov(
				Twist3d(
					linVel.x,
					linVel.y,
					linVel.z,
					angVel.X(),
					angVel.Y(),
					angVel.Z(),
				),
			)
			twist_update_vec = StateMembers.NONE
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
			covariance_rotated = (covariance_rotated + prev_covar_rotated) * dt

			self.log.debug("Previous measurement covariance: %s", prev_measurement.value.cov)
			self.log.debug("Previous measurement covariance rotated: %s", prev_covar_rotated)
			self.log.debug("Final twist covariance: %s", covariance_rotated)

			# Now pass this on to prepareTwist, which will convert it to the
			# required frame
			res = self.prepare_twist(
				source,
				twist,
				update_vector,
				pose.stamp,
			)
		else:
			res = None
		# 7f. Update the previous measurement and measurement covariance
		source.previous_measurements.append(pose)
		return res

	def prepare_pose(self, source: DataSource, msg: Stamped[Pose3dCov], update_vector: StateMembers, mode: SensorMode, imu_data: bool = False) -> Measurement | None:
		# Handle issues where frame_id data is not filled out properly
		# @todo: verify that this is necessary still. New IMU handling may
		# have rendered this obsolete.
		# Otherwise, we should use our target frame
		# pose_tmp.frame_id_ = final_target_frame if (mode == SensorMode.DIFFERENTIAL and not imu_data) else msg.header.frame_id

		# self.log.debug(
		# 	"Final target frame for " << topic_name << " is " <<
		# 	final_target_frame << "\n")

		# Handle bad (empty) quaternions
		mean_quat = msg.value.mean.rotation().getQuaternion()
		if mean_quat.W() == 0 and mean_quat.X() == 0 and mean_quat.Y() == 0 and mean_quat.Z() == 0:
			orientation = Quaternion(1.0, 0.0, 0.0, 0.0)

			if (update_vector & StateMembers.POS_ANG):
				msg = (f"The {source.name} message contains an invalid orientation quaternion, "
					"but its configuration is such that orientation data is being used."
					" Correcting...")

				self.addDiagnostic(logging.WARNING, source.name + "_orientation", msg, False)
		else:
			orientation = mean_quat
			if np.abs(orientation.norm() - 1.0) > 0.01:
				# RCLCPP_WARN_ONCE("An input was not normalized, this should NOT happen, but will normalize.")
				orientation = orientation.normalize()
		
		if orientation != msg.value.mean.rotation().getQuaternion():
			msg.value.mean = Pose3d(Rotation3d(orientation), msg.value.mean.translation())
		

		# 1. Get the measurement into a tf-friendly transform (pose) object
		pose_tmp = Stamped(
			Pose3d(
				Rotation3d(orientation),
				msg.value.mean.translation(),
			),
			msg.stamp,
		)

		# 2. Get the target frame transformation
		sensor_to_robot = source.sensor_to_robot

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
		if imu_data:
			# We have to treat IMU orientation data differently. Even though we are
			# dealing with pose data when we work with orientations, for IMUs, the
			# frame_id is the frame in which the sensor is mounted, and not the
			# coordinate frame of the IMU. Imagine an IMU that is mounted facing
			# sideways. The pitch in the IMU frame becomes roll for the vehicle. This
			# means that we need to rotate roll and pitch angles by the IMU's
			# mounting yaw offset, and we must apply similar treatment to its update
			# mask and covariance.
			rot = rot3_flatten(sensor_to_robot.rotation())
		else:
			rot = sensor_to_robot.rotation()

		# Now copy the mask values back into the update vector: any row with a
		# significant vector length indicates that we want to set that variable to
		# true in the update vector.
		update_vector = update_mask_rotation(update_vector, rot, StateMembers.POS_LIN, StateMembers.POS_ANG)

		# 5a. We'll need to rotate the covariance as well. Create a container and
		# copy over the covariance data
		covariance = msg.value.cov

		# 5b. Now rotate the covariance: create an augmented matrix that
		# contains a 3D rotation matrix in the upper-left and lower-right
		# quadrants, with zeros elsewhere.

		# Transform pose covariance due to a different pose source origin
		if False and can_src_transform:
			rot6d = rot3_to_mat6(source_frame_trans.rotation())
			# since the transformation is a post-multiply
			covariance = rot6d.transpose() @ covariance @ rot6d

		rot6d = rot3_to_mat6(rot)

		# Now carry out the rotation
		pose = msg.value.transformCov(rot)
		# covariance_rotated = rot6d * covariance * rot6d.transpose()

		self.log.debug("After rotating into the robot frame, covariance is %s", pose.cov)

		# 6a. For IMU data, the transform that we get is the transform from the
		# body frame of the robot (e.g., base_link) to the mounting frame of the
		# robot. It is *not* the coordinate frame in which the IMU orientation data
		# is reported. If the IMU is mounted in a non-neutral orientation, we need
		# to remove those offsets, and then we need to potentially "swap" roll and
		# pitch. Note that this transform does NOT handle NED.ENU conversions.
		# Data is assumed to be in the ENU frame when it is received.
		if False and imu_data:
			# First, convert the transform and measurement rotation to RPY
			# @todo: There must be a way to handle this with quaternions. Need to
			# look into it.
			roll_offset = 0.0
			pitch_offset = 0.0
			yaw_offset = 0.0
			roll = 0.0
			pitch = 0.0
			yaw = 0.0
			ros_filter_utilities.quatToRPY(
				target_frame_trans.getRotation(),
				roll_offset, pitch_offset, yaw_offset)
			ros_filter_utilities.quatToRPY(pose_tmp.getRotation(), roll, pitch, yaw)

			# 6b. Apply the offset (making sure to bound them), and throw them in a
			# vector
			rpy_angles = (
				angles.normalize_angle(roll - roll_offset),
				angles.normalize_angle(pitch - pitch_offset),
				angles.normalize_angle(yaw - yaw_offset))

			# 6c. Now we need to rotate the roll and pitch by the yaw offset value.
			# Imagine a case where an IMU is mounted facing sideways. In that case
			# pitch for the IMU's world frame is roll for the robot.
			mat: Matrix3x3
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
			return self._prepare_pose_differential(source, pose_tmp, update_vector)
		# make pose refer to the baseLinkFrame as source
		# can_src_transform == true => ( sourceFrame != baseLinkFrameId_ )
		# if (can_src_transform) {
		# 	pose_tmp.setData(pose_tmp * source_frame_trans)
		# }

		# 7g. If we're in relative mode, remove the initial measurement
		if mode == SensorMode.RELATIVE:
			if source.initial_measurement is None:
				source.initial_measurement = pose_tmp
			initial_measurement = source.initial_measurement
			pose_tmp.value = pose_tmp.value.relativeTo(initial_measurement)

		# 7h. Apply the target frame transformation to the pose object.
		pose_final = pose_tmp.value.transformBy(sensor_to_robot)

		# 7i. Finally, copy everything into our measurement and covariance
		# objects
		measurement = Measurement(msg.stamp, source, update_vector=update_vector)
		measurement.update(pose_final)

		# 8. Handle 2D mode
		if self.config.force_2d:
			measurement = self._force_2d(measurement)

		retVal = True
		return retVal

	def prepare_twist(self, source: DataSource, ts: Timestamp, twist: Twist3dCov, update_vector: StateMembers) -> Measurement:
		# 1. Get the measurement into two separate vector objects.
		twist_lin = np.array([twist.mean.dx, twist.mean.dy, twist.mean.dz])
		twist_rot = np.array([twist.mean.rx, twist.mean.ry, twist.mean.rz])

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
		
		maskLin = mask_to_mat(update_vector, StateMembers.VEL_LIN)
		maskRot = mask_to_mat(update_vector, StateMembers.VEL_ANG)

		# 3. We'll need to rotate the covariance as well
		covariance_rotated = np.zeros((len(StateMembers.TWIST), len(StateMembers.TWIST)), dtype=float)
		covariance_rotated[:] = twist.cov[:]

		# self.log.debug(
		# 	"Original measurement as tf object:\nLinear: " <<
		# 	twist_lin << "Rotational: " << meas_twist_rot <<
		# 	"\nOriginal update vector:\n" <<
		# 	update_vector << "\nOriginal covariance matrix:\n" <<
		# 	covariance_rotated << "\n")

		# 4. We need to transform this into the target frame (probably base_link)
		sensor_to_robot = source.sensor_to_robot

		# Transform to correct frame. Note that we can get linear velocity
		# as a result of the sensor offset and rotational velocity
		rot_mat = rot3_to_mat(sensor_to_robot.rotation())
		twist_rot = rot_mat @ twist_rot
		twist_lin = (rot_mat @ twist_lin) + np.cross([sensor_to_robot.x, sensor_to_robot.y, sensor_to_robot.z], state_twist_rot)
		maskLin = rot_mat @ maskLin
		maskRot = rot_mat @ maskRot

		# Now copy the mask values back into the update vector
		update_vector &= mat_to_mask(maskLin, StateMembers.VEL_LIN)
		update_vector &= mat_to_mask(maskRot, StateMembers.VEL_ANG)

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
		rot6d = rot3_to_mat6(sensor_to_robot.rotation())

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
			measurement = self._force_2d(measurement)
		return measurement
	
	def _force_2d(self, measurement: Measurement) -> Measurement:
		"Flatten a Measurement into 2D"
		m3 = StateMembers.Z | StateMembers.Roll | StateMembers.Pitch | StateMembers.Vz | StateMembers.Vroll | StateMembers.Vpitch | StateMembers.Az
		measurement[m3] = 0.0
		for m in m3:
			mi = m.idx()
			measurement.measurement[mi] = 0.0
			measurement.covariance[mi, mi] = 1e-6
		measurement.update_vector |= m3
	
	def prepare_acceleration(self, source: DataSource, ts: Timestamp, accel: LinearAcceleration3dCov, update_vector: StateMembers, mode: SensorMode) -> Measurement | None:
		# 1. Get the measurement into a vector
		acc_tmp = accel.mean_vec()

		# 3. We'll need to rotate the covariance as well
		covariance_rotated = np.copy(accel.cov)

		self.log.debug("Original measurement as tf object: %s", acc_tmp)
		self.log.debug("Original update vector: %s", update_vector)
		self.log.debug("Original covariance matrix: %s", covariance_rotated)

		# 4. We need to transform this into the target frame (probably base_link)
		# It's unlikely that we'll get a velocity measurement in another frame, but
		# we have to handle the situation.
		target_frame_trans = source.sensor_to_robot
		state = self._filter.state

		# Transform to correct frame, prior to removal of gravity.
		state_twist_rot = state[StateMembers.VEL_ANG.idxs()]
		acc_tmp = target_frame_trans.rotation() * acc_tmp \
			+ target_frame_trans.getOrigin().cross(self._angular_acceleration) \
			- target_frame_trans.getOrigin().cross(state_twist_rot).cross(state_twist_rot);

		# We don't know if the user has already handled the removal
		# of normal forces, so we use a parameter
		if source.remove_gravitational_acceleration:
			normAcc = np.array([0, 0, gravitational_acceleration])
			if np.abs(msg.orientation_covariance[0] + 1) < 1e-9:
				# Imu message contains no orientation, so we should use orientation
				# from filter state to transform and remove acceleration
				stateTmp = Rotation3d(
					state[StateMembers.Roll.idx()],
					state[StateMembers.Pitch.idx()],
					state[StateMembers.Yaw.idx()],
				)

				# transform state orientation to IMU frame
				trans = Transform3d(
					stateTmp + target_frame_trans.rotation(),
					Translation3d()
				)
				rotNorm = (-trans.rotation()) * normAcc
			else:
				curAttitude = msg.orientation
				if np.abs(curAttitude.length() - 1.0) > 0.01:
					RCLCPP_WARN_ONCE(
						get_logger(),
						"An input was not normalized, this should NOT happen, but will normalize.")
					curAttitude.normalize()
				trans = Transform3d(
					curAttitude,
					Translation3d()
				)
				if mode != SensorMode.RELATIVE:
					# curAttitude is the true world-frame attitude of the sensor
					rotNorm = (-trans.rotation()) * normAcc
				else:
					# curAttitude is relative to the initial pose of the sensor.
					# Assumption: IMU sensor is rigidly attached to the base_link
					# (but a static rotation is possible).
					rotNorm = (-target_frame_trans.rotation()) * (-trans.rotation()) * normAcc
			acc_tmp.setX(acc_tmp.getX() - rotNorm.getX())
			acc_tmp.setY(acc_tmp.getY() - rotNorm.getY())
			acc_tmp.setZ(acc_tmp.getZ() - rotNorm.getZ())

			self.log.debug("Orientation is %s", trans.rotation())
			self.log.debug("Acceleration due to gravity is %s", rotNorm)
			self.log.debug("After removing acceleration due to gravity, acceleration is %s", acc_tmp)

		# 2. robot_localization lets users configure which variables from the sensor
		# should be
		#    fused with the filter. This is specified at the sensor level. However,
		#    the data may go through transforms before being fused with the state
		#    estimate. In that case, we need to know which of the transformed
		#    variables came from the pre-transformed "approved" variables (i.e., the
		#    ones that had "true" in their xxx_config parameter). To do this, we
		#    create a pose from the original upate vector, which contains only zeros
		#    and ones. This pose goes through the same transforms as the measurement.
		#    The non-zero values that result will be used to modify the
		#    update_vector.
		# Now use the mask values to determine which update vector values should be
		# true
		update_vector = update_mask_rotation(update_vector, target_frame_trans.rotation(), StateMembers.ACC_LIN)

		# RF_DEBUG(
		# msg->header.frame_id <<
		# 	"->" << target_frame << " transform:\n" <<
		# 	target_frame_trans << "\nAfter applying transform to " <<
		# 	target_frame << ", update vector is:\n" <<
		# 	update_vector << "\nAfter applying transform to " <<
		# 	target_frame << ", measurement is:\n" <<
		# 	acc_tmp << "\n");

		# 5. Now rotate the covariance: create an augmented
		# matrix that contains a 3D rotation matrix in the
		# upper-left and lower-right quadrants, and zeros
		# elsewhere
		rot_mat = rot3_to_mat(target_frame_trans.rotation())
		# Carry out the rotation
		covariance_rotated = rot_mat @ covariance_rotated @ rot_mat.T

		self.log.debug("Transformed covariance is %s", covariance_rotated)

		# 6. Store our corrected measurement and covariance
		measurement = Measurement(ts, source, update_vector=update_vector)
		measurement.measure(StateMembers.Ax, acc_tmp.x)
		measurement.measure(StateMembers.Ay, acc_tmp.y)
		measurement.measure(StateMembers.Az, acc_tmp.z)

		# Copy the covariances
		measurement.copy_covariance(StateMembers.ACC_LIN, covariance_rotated)

		# 7. Handle 2D mode
		if self.config.force_2d:
			measurement = self._force_2d(measurement)

		return measurement
	
	def handle_acceleration(self, source: DataSource[Stamped[LinearAcceleration3dCov]], msg: Stamped[LinearAcceleration3dCov], update_vector: StateMembers, mode: SensorMode):
		if not self._check_timestamp(source, msg.stamp):
			return
		
		self.log.debug("Update vector for %s is:", source.name)
		measurement = Measurement(msg.stamp, source)

		# Make sure we're actually updating at least one of these variables
		update_vector_corrected = StateMembers(update_vector)

		# Prepare the twist data for inclusion in the filter
		if measurement := self.prepare_acceleration(source, msg.stamp, msg.value, update_vector_corrected, mode):
			# Store the measurement. Add an "acceleration" suffix so we know what
			# kind of measurement we're dealing with when we debug the core filter
			# logic.
			self._enqueue_measurement(measurement, source.rejection_threshold)

			self.log.debug("Enqueued new measurement for %s_acceleration", source.name)
		else:
			self.log.debug("Did *not* enqueue measurement for %s_acceleration", source.name)

		source.last_message_time = msg.stamp
	
	def handle_twist(self, source: DataSource, ts: Timestamp, twist: Twist3dCov, update_vector: StateMembers, rejection_threshold: float):
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
	
	def handle_pose(self, source: DataSource, pose: Pose3dCov, ts: Timestamp, update_vector: StateMembers, rejection_threshold: float, mode: SensorMode):
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
		# meas.topic_name_ = topic_name
		# meas.measurement_ = measurement
		# meas.covariance_ = measurement_covariance
		# meas.update_vector_ = update_vector
		# meas.time_ = time
		# meas.mahalanobis_thresh_ = mahalanobis_thresh
		# meas.latest_control_ = latest_control_
		# meas.latest_control_time_ = latest_control_time_
		self._replay.enqueue_measurement(measurement)
	
	def reset(self):
		# Get rid of any initial poses (pretend we've never had a measurement)
		self._replay.clear()

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
