from typing import Literal, overload, TypeVar, TYPE_CHECKING, Any
from numpy.typing import NDArray, ArrayLike
import logging
from datetime import timedelta
from dataclasses import dataclass
from enum import IntFlag, auto, Flag, Enum
from abc import abstractmethod

import numpy as np

from typedef.geom_cov import Pose3dCov, Twist3dCov
from util.timestamp import Timestamp, Stamped
from util.clock import Clock
from . import angles
from ..util.replay import GenericFilter

if TYPE_CHECKING:
	from .filter import DataSource

T = TypeVar('T')

@overload
def block(idxs: list[int] | IntFlag) -> np.ndarray[int]: ...
@overload
def block(base: np.ndarray[T] | ArrayLike, idxs: list[int] | IntFlag) -> np.ndarray[T]: ...
def block(arg0: np.ndarray[T] | ArrayLike | list[int] | IntFlag, arg1 = None) -> np.ndarray:
	if arg1 is None:
		base = np.asarray(arg0)
		idxs = arg1
	else:
		base = None
		idxs = arg0
	
	if isinstance(idxs, IntFlag):
		idxs = np.array(list(idxs), dtype=int)
	
	if base is not None:
		return base[idxs, :][:, idxs]
	raise NotImplemented
	# return base[idxs, :][:, idxs]

class StateMember(Enum):
	NONE = 0
	X = 1
	Y = 2
	Z = 3
	Roll = 4
	Pitch = 5
	Yaw = 6
	Vx = 7
	Vy = 8
	Vz = 9
	Vroll = 10
	Vpitch = 11
	Vyaw = 12
	Ax = 13
	Ay = 14
	Az = 15

	def __or__(self, __value: Any):
		if isinstance(__value, StateMember):
			return StateMembers(self, __value)
		if isinstance(__value, StateMembers):
			return StateMembers(self, *__value)
		return super().__or__(__value)

class StateMembersList:
	def __init__(self, *members: StateMember, flag: int = 0) -> None:
		self.flag = flag
		for member in members:
			self.flag |= (1 << member.value)
	def __bool__(self):
		return self.flag != 0
	def __len__(self):
		return self.flag.bit_count()
	def __iter__(self):
		for i in range(15):
			if (self.flag & (1 << i)) != 0:
				yield StateMember(i)
	def __and__(self, v: Any):
		pass
	def __or__(self, __value: Any):
		if isinstance(__value, StateMembers):
			return StateMembers(flag=self.flag | __value.flag)
		if isinstance(__value, StateMember):
			return StateMembers(flag=self.flag | 1 << __value.value)
		return super().__or__(__value)

class StateMembers(IntFlag):
	_ignore_ = { 'POS_LIN', 'POS_ANG', 'POSE', 'VEL_LIN', 'VEL_ANG', 'TWIST', 'ACC_LIN', 'idxs'}
	NONE = 0
	X = auto()
	Y = auto()
	Z = auto()
	Roll = auto()
	Pitch = auto()
	Yaw = auto()
	Vx = auto()
	Vy = auto()
	Vz = auto()
	Vroll = auto()
	Vpitch = auto()
	Vyaw = auto()
	Ax = auto()
	Ay = auto()
	Az = auto()

	POS_LIN: 'StateMembers'
	POS_ANG: 'StateMembers'
	POSE: 'StateMembers'
	VEL_LIN: 'StateMembers'
	VEL_ANG: 'StateMembers'
	TWIST: 'StateMembers'
	ACC_LIN: 'StateMembers'

	# @classmethod
	def idxs(self) -> list[int]:
		return np.log2(np.array(list(self), dtype=int))
	
	def idx(self) -> int:
		return int(np.log2(int(self)))
	
	def as_numpy(self) -> np.ndarray[int]:
		return np.asarray(list(self), dtype=int)

StateMembers.POS_LIN = StateMembers.X | StateMembers.Y | StateMembers.Z
StateMembers.POS_ANG = StateMembers.Roll | StateMembers.Pitch | StateMembers.Yaw
StateMembers.POSE = StateMembers.POS_LIN | StateMembers.POS_ANG
StateMembers.VEL_LIN = StateMembers.Vx | StateMembers.Vy | StateMembers.Vz
StateMembers.VEL_ANG = StateMembers.Vroll | StateMembers.Vpitch | StateMembers.Vyaw
StateMembers.TWIST = StateMembers.VEL_LIN | StateMembers.VEL_ANG
StateMembers.ACC_LIN = StateMembers.Ax | StateMembers.Ay | StateMembers.Az

class ControlMembers(Flag):
	Vx = auto()
	Vy = auto()
	Vz = auto()
	Vroll = auto()
	Vpitch = auto()
	Vyaw = auto()


class Measurement:
	ts: Timestamp
	mahalanobis_threshold: float | None = None
	"The Mahalanobis distance threshold in number of sigmas"
	latest_control_time: Timestamp | None = None
	"The time stamp of the most recent control term (needed for lagged data)"
	source: 'DataSource'
	"The topic name for this measurement. Needed for capturing previous state values for new measurements. "

	update_vector: StateMembers
	"""
	This defines which variables within this measurement actually get passed
	into the filter.
	"""
	latest_control: Any
	"The most recent control vector (needed for lagged data)"

	measurement: NDArray
	"The measurement and its associated covariance"
	covariance: NDArray

	def __init__(self, ts: Timestamp, source: 'DataSource', *, update_vector: StateMembers = StateMembers.NONE) -> None:
		self.ts = ts
		self.source = source
		self.update_vector = update_vector
		self.measurement = np.zeros(15, dtype=float)
		self.covariance = np.zeros((15, 15), dtype=float)
		self.mahalanobis_threshold = None

	def update(self, data: Pose3dCov | Twist3dCov):
		if isinstance(data, Pose3dCov):
			self.measure(StateMember.X, data.mean.X())
			self.measure(StateMember.Y, data.mean.Y())
			self.measure(StateMember.Z, data.mean.Z())
			# The filter needs roll, pitch, and yaw values instead of quaternions
			self.measure(StateMember.Roll,  data.mean.rotation().X())
			self.measure(StateMember.Pitch, data.mean.rotation().Y())
			self.measure(StateMember.Yaw,   data.mean.rotation().Z())

			self.copy_covariance(StateMembers.POSE, data.cov)
		elif isinstance(data, Twist3dCov):
			pass
	def measure(self, idxs: StateMembers, value: float | np.ndarray[float], cov: float | np.ndarray[float] | None = None):
		self.measurement[idxs.idxs()] = value
		if cov is not None:
			cov_idxs = np.diag_indices(15)[idxs.idxs()]
			self.covariance[cov_idxs] = cov
	
	def copy_covariance(self, idxs: StateMembers, cov_src: np.ndarray[float]):
		pass

	@property
	def mean_dense(self):
		return self.measurement
	@property
	def covariance_dense(self):
		return self.covariance

@dataclass
class FilterSnapshot:
	state: np.ndarray
	estimate_error_covariance: np.ndarray
	last_measurement_ts: Timestamp

	@property
	def ts(self):
		return self.last_measurement_ts


S = Literal[15]

class FilterBase(GenericFilter[Measurement, FilterSnapshot]):
	debug: bool
	estimate_error_covariance: np.ndarray[float, tuple[S, S]]
	process_noise_covariance: np.ndarray[float, tuple[S, S]]
	"Gets the filter's process noise covariance"

	dynamic_process_noise_covariance: np.ndarray[float, tuple[S, S]]
	def __init__(self, log: logging.Logger, clock: Clock, state_size: int = 15):
		self.log = log
		self.debug = False
		self.is_initialized = False
		"True if we've received our first measurement, false otherwise"
		self.state_size = state_size
		"The estimated error covariance"
		self.use_control = False
		"Whether or not we apply the control term"
		self.use_dynamic_process_noise_covariance = False

		TWIST_SIZE = len(StateMembers.TWIST)
		self.control_update_vector = (TWIST_SIZE, 0)
		self.control_acceleration = np.zeros(TWIST_SIZE, dtype=bool)
		self.latest_control = Stamped(
			np.zeros(TWIST_SIZE, dtype=np.float32),
			Timestamp.invalid(clock),
		)
		self.predicted_state = np.zeros(state_size, dtype=np.float32)
		"The filter's predicted state, i.e., the state estimate before correct() is called."
		self.state = np.zeros((state_size), dtype=float)
		self.covariance_epsilon = np.zeros((state_size, state_size), dtype=np.float32)
		self.dynamic_process_noise_covariance = np.zeros((state_size, state_size), dtype=np.float32)
		self.estimate_error_covariance = np.zeros((state_size, state_size), dtype=np.float32)
		self.process_noise_covariance = np.zeros((state_size, state_size), dtype=np.float32)
		self.transfer_function = np.zeros((state_size, state_size), dtype=np.float32)
		self.transfer_function_jacobian = np.zeros((state_size, state_size), dtype=np.float32)
		"""
		If true, uses the robot's vehicle state and the static process noise
		covariance matrix to generate a dynamic process noise covariance matrix"""

		self.clock = clock
		self.last_measurement_ts = Timestamp.invalid(clock)
		"Gets the most recent measurement time"
		self.control_ts = Timestamp.invalid(clock)
		"The time at which the control term was issued"
		self.sensor_timeout = timedelta(0)
		"Gets the sensor timeout value"

		self.reset()
	
	def reset(self):
		"Resets filter to its unintialized state"
		self.is_initialized = False

		# Clear the state and predicted state
		self.state[:] = 0
		self.predicted_state[:] = 0
		self.control_acceleration[:] = False

		# Prepare the invariant parts of the transfer
		# function
		self.transfer_function[:] = np.eye(self.state_size)

		# Clear the Jacobian
		self.transfer_function_jacobian[:] = 0

		# Set the estimate error covariance. We want our measurements
		# to be accepted rapidly when the filter starts, so we should
		# initialize the state's covariance with large values.
		self.estimate_error_covariance[:] = np.eye(self.state_size) * 1e-9

		# Set the epsilon matrix to be a matrix with small values on the diagonal
		# It is used to maintain the positive-definite property of the covariance
		self.covariance_epsilon[:] = np.eye(self.state_size) * 0.001

		# Assume 30Hz from sensor data (configurable)
		self.sensor_timeout = timedelta(seconds=0.033333333)

		# Initialize our last update and measurement times
		self.last_measurement_ts = Timestamp.invalid(self.clock)

		# These can be overridden via the launch parameters,
		# but we need default values.
		self.process_noise_covariance[:] = 0
		print(StateMembers.X.idx())
		self.process_noise_covariance[StateMembers.X.idx(), StateMembers.X.idx()] = 0.05
		self.process_noise_covariance[StateMembers.Y.idx(), StateMembers.Y.idx()] = 0.05
		self.process_noise_covariance[StateMembers.Z.idx(), StateMembers.Z.idx()] = 0.06
		self.process_noise_covariance[StateMembers.Roll.idx(), StateMembers.Roll.idx()] = 0.03
		self.process_noise_covariance[StateMembers.Pitch.idx(), StateMembers.Pitch.idx()] = 0.03
		self.process_noise_covariance[StateMembers.Yaw.idx(), StateMembers.Yaw.idx()] = 0.06
		self.process_noise_covariance[StateMembers.Vx.idx(), StateMembers.Vx.idx()] = 0.025
		self.process_noise_covariance[StateMembers.Vy.idx(), StateMembers.Vy.idx()] = 0.025
		self.process_noise_covariance[StateMembers.Vz.idx(), StateMembers.Vz.idx()] = 0.04
		self.process_noise_covariance[StateMembers.Vroll.idx(), StateMembers.Vroll.idx()] = 0.01
		self.process_noise_covariance[StateMembers.Vpitch.idx(), StateMembers.Vpitch.idx()] = 0.01
		self.process_noise_covariance[StateMembers.Vyaw.idx(), StateMembers.Vyaw.idx()] = 0.02
		self.process_noise_covariance[StateMembers.Ax.idx(), StateMembers.Ax.idx()] = 0.01
		self.process_noise_covariance[StateMembers.Ay.idx(), StateMembers.Ay.idx()] = 0.01
		self.process_noise_covariance[StateMembers.Az.idx(), StateMembers.Az.idx()] = 0.015

		self.dynamic_process_noise_covariance[:] = self.process_noise_covariance

	def snapshot(self) -> FilterSnapshot:
		return FilterSnapshot(
			np.copy(self.state),
			np.copy(self.estimate_error_covariance),
			self.last_measurement_ts,
		)
	def restore(self, snapshot: FilterSnapshot):
		self.state = snapshot.state
		self.estimate_error_covariance = snapshot.estimate_error_covariance
		self.last_measurement_ts = snapshot.last_measurement_ts

	def differentiate(self, now: Timestamp):
		dt = now - self.last_diff_time
		state = self.state[:]
		new_state_twist_rot = state[(
			StateMembers.Vroll.idx(),
			StateMembers.Vpitch.idx(),
			StateMembers.Vyaw.idx(),
		)]
		self.angular_acceleration = (new_state_twist_rot - self.last_state_twist_rot) / dt
		cov = self.estimate_error_covariance
		ORIENTATION_SIZE = len(StateMembers.POS_LIN)
		for i in range(ORIENTATION_SIZE):
			for j in range(ORIENTATION_SIZE):
				self.angular_acceleration_cov[i, j] = cov[i + ORIENTATION_V_OFFSET, j + ORIENTATION_V_OFFSE] * 2. / ( dt * dt )
		self.last_state_twist_rot = new_state_twist_rot
		self.last_diff_time = now

	def validate_delta(self, delta: timedelta):
		"Ensures a given time delta is valid (helps with bag file playback"
		pass

	@abstractmethod
	def predict(self, now: Timestamp, delta: timedelta):
		"""
		Carries out the predict step in the predict/update cycle.

		Projects the state and error matrices forward using a model of the
		vehicle's motion. This method must be implemented by subclasses.

		@param[in] reference_time - The time at which the prediction is being made
		@param[in] delta - The time step over which to predict.
		"""
		pass

	@abstractmethod
	def process_measurement(self, measurement: Measurement):
		pass

	def computeDynamicProcessNoiseCovariance(self, state: np.ndarray[float, S]):
		"""
		Computes a dynamic process noise covariance matrix using the
	 		parameterized state This allows us to, e.g., not increase the pose
	 		covariance values when the vehicle is not moving
	 		@param[in] state - The STATE_SIZE state vector that is used to generate the
	 		dynamic process noise covariance
		"""
		# A more principled approach would be to get the current velocity from the
		# state, make a diagonal matrix from it, and then rotate it to be in the
		# world frame (i.e., the same frame as the pose data). We could then use this
		# rotated velocity matrix to scale the process noise covariance for the pose
		# variables as rotatedVelocityMatrix * poseCovariance *
		# rotatedVelocityMatrix' However, this presents trouble for robots that may
		# incur rotational error as a result of linear motion (and vice-versa).
		# Instead, we create a diagonal matrix whose diagonal values are the vector
		# norm of the state's velocity. We use that to scale the process noise
		# covariance.
		velocity_matrix = np.zeros(len(StateMembers.TWIST), dtype=float)
		np.fill_diagonal(velocity_matrix, np.linalg.norm(state[list(StateMembers.TWIST)]))

		twist_idxs = block(StateMembers.TWIST)
		self.dynamic_process_noise_covariance[twist_idxs] = velocity_matrix @ self.process_noise_covariance[twist_idxs] @ velocity_matrix.T
	
	def debug_method(self, *args):
		pass

	def correct(self, measurement: Measurement):
		"""
		Carries out the correct step in the predict/update cycle. This
		method must be implemented by subclasses.
		@param[in] measurement - The measurement to fuse with the state estimate
		"""
		pass

	@property
	def control(self) -> Stamped[np.floating[T]]:
		"The control vector currently being used"
		return self.latest_control

	def snapshot(self):
		pass

	def getState(self) -> np.ndarray[float, S]:
		"Gets the filter state"
		pass

	def checkMahalanobisThreshold(self, innovation, innovation_covariance, n_sigmas: float) -> bool:
		squared_mahalanobis = np.dot(innovation, (innovation_covariance @ innovation))
		threshold = n_sigmas * n_sigmas

		if squared_mahalanobis >= threshold:
			self.log.debug("Innovation mahalanobis distance test failed. Squared Mahalanobis is: %s", squared_mahalanobis)
			self.log.debug("Threshold is: %s", threshold)
			self.log.debug("Innovation is: %s", innovation)
			self.log.debug("Innovation covariance is: %s", innovation_covariance)
			return False
		return True

	def process_measurement(self, measurement: Measurement):
		"""
		Does some final preprocessing, carries out the predict/update cycle
		@param[in] measurement - The measurement object to fuse into the filter
		"""
		with self.debug_method(measurement.source_name):
			delta = timedelta(0)

			# If we've had a previous reading, then go through the predict/update
			# cycle. Otherwise, set our state and covariance to whatever we get
			# from this measurement.
			if self.is_initialized:
				# Determine how much time has passed since our last measurement
				delta = measurement.ts - self.last_measurement_ts

				self.log.debug("Filter is already initialized. Carrying out predict/correct loop...")
				self.log.debug("Measurement time is %s, last measurement time is %s, delta is %s", measurement.ts.as_seconds(), self.last_measurement_ts.as_seconds(), delta.total_seconds())

				# Only want to carry out a prediction if it's
				# forward in time. Otherwise, just correct.
				if delta.total_seconds() > 0:
					self.validateDelta(delta)
					self.predict(measurement.ts, delta)

					# Return this to the user
					self.predicted_state = np.copy(self.state)

				self.correct(measurement)
			else:
				self.log.debug("First measurement. Initializing filter.")

				# Initialize the filter, but only with the values we're using
				measurement_length = measurement.update_vector_.size()
				for i in range(measurement_length):
					self.state[i] = measurement.mean_dense[i] if measurement.update_vector[i] else self.state[i]

				# Same for covariance
				for i in range(measurement_length):
					for j in range(measurement_length):
						self.estimate_error_covariance[i, j] = (
							measurement.covariance_dense[i, j]
							if (measurement.update_vector[i] and measurement.update_vector[j])
							else self.estimate_error_covariance[i, j]
						)

				self.is_initialized = True;

			if delta.total_seconds() > 0:
				# Update the last measurement and update time.
				# The measurement time is based on the time stamp of the
				# measurement, whereas the update time is based on this
				# node's current ROS time. The update time is used to
				# determine if we have a sensor timeout, whereas the
				# measurement time is used to calculate time deltas for
				# prediction and correction.
				self.last_measurement_ts = measurement.ts

	def set_control(self, control: np.ndarray[float, S], control_time: Timestamp):
		"""
		Sets the most recent control term
		@param[in] control - The control term to be applied
		@param[in] control_time - The time at which the control in question was
		"""
		self.control = control
		self.control_ts = control_time

	def setControlParams(
		self,
		update_vector: ControlMembers,
		control_timeout: timedelta,
		acceleration_limits: list[float],
		acceleration_gains: list[float],
		deceleration_limits: list[float],
		deceleration_gains: list[float],
	):
		"""
		Sets the control update vector and acceleration limits
		@param[in] update_vector - The values the control term affects
		@param[in] control_timeout - Timeout value, in seconds, after which a control is considered stale
		@param[in] acceleration_limits - The acceleration limits for the control variables
		@param[in] acceleration_gains - Gains applied to the control term-derived acceleration
		@param[in] deceleration_limits - The deceleration limits for the control variables
		@param[in] deceleration_gains - Gains applied to the control term-derived deceleration
		"""
		self.use_control = True
		self.control_update_vector = update_vector
		self._control_timeout = control_timeout
		self._acceleration_limits = acceleration_limits
		self._acceleration_gains = acceleration_gains
		self._deceleration_limits = deceleration_limits
		self._deceleration_gains = deceleration_gains
	def computeControlAcceleration(self, state: float, control: float, acceleration_limit: float, acceleration_gain: float, deceleration_limit: float, deceleration_gain: float):
		"""
		Method for settings bounds on acceleration values derived from
		controls
		@param[in] state - The current state variable (e.g., linear X velocity)
		@param[in] control - The current control commanded velocity corresponding
		to the state variable
		@param[in] acceleration_limit - Limit for acceleration (regardless of
		driving direction)
		@param[in] acceleration_gain - Gain applied to acceleration control error
		@param[in] deceleration_limit - Limit for deceleration (moving towards
		zero, regardless of driving direction)
		@param[in] deceleration_gain - Gain applied to deceleration control error
		@return a usable acceleration estimate for the control vector
		"""
		# FB_DEBUG("---------- FilterBase::computeControlAcceleration ----------\n");

		error = control - state
		same_sign = (np.abs(error) <= np.abs(control) + 0.01)
		set_point = control if same_sign else 0.0
		decelerating = np.abs(set_point) < np.abs(state);
		limit = acceleration_limit
		gain = acceleration_gain

		if (decelerating):
			limit = deceleration_limit
			gain = deceleration_gain

		final_accel = np.clip(gain * error, -limit, limit)

		# FB_DEBUG(
		# 	"Control value: " <<
		# 	control << "\n" <<
		# 	"State value: " << state << "\n" <<
		# 	"Error: " << error << "\n" <<
		# 	"Same sign: " << (same_sign ? "true" : "false") << "\n" <<
		# 	"Set point: " << set_point << "\n" <<
		# 	"Decelerating: " << (decelerating ? "true" : "false") << "\n" <<
		# 	"Limit: " << limit << "\n" <<
		# 	"Gain: " << gain << "\n" <<
		# 	"Final is " << final_accel << "\n");

		return final_accel

	def wrapStateAngles(self):
		"Keeps the state Euler angles in the range [-pi, pi]"
		idxs = StateMembers.VEL_ANG.idxs()
		self.state[idxs] = angles.normalize_angle(self.state[idxs])

	def checkMahalanobisThreshold(self, innovation: np.ndarray, innovation_covariance: np.ndarray, n_sigmas: float) -> bool:
		"""
		Tests if innovation is within N-sigmas of covariance. Returns true
		if passed the test.
		@param[in] innovation - The difference between the measurement and the
		state
		@param[in] innovation_covariance - The innovation error
		@param[in] n_sigmas - Number of standard deviations that are considered
		acceptable
		"""
		squared_mahalanobis = np.dot(innovation, (innovation_covariance @ innovation))
		threshold = n_sigmas * n_sigmas

		if (squared_mahalanobis >= threshold):
			# FB_DEBUG(
			# "Innovation mahalanobis distance test failed. Squared Mahalanobis is: " <<
			# 	squared_mahalanobis << "\nThreshold is: " << threshold << "\n" <<
			# 	"Innovation is: " << innovation << "\n" <<
			# 	"Innovation covariance is:\n" <<
			# 	innovation_covariance << "\n");
			pass

		return squared_mahalanobis < threshold

	def prepareControl(self, reference_time: Timestamp, delta: timedelta):
		"""
		Converts the control term to an acceleration to be applied in the
		prediction step
		@param[in] reference_time - The time of the update (measurement used in the
		prediction step)
		"""
		self.control_acceleration[:] = 0

		if self.use_control:
			timed_out = (reference_time - self.latest_control_time >= self._control_timeout);

			if timed_out:
				# FB_DEBUG(
				# 	"Control timed out. Reference time was " <<
				# 	reference_time.nanoseconds() << ", latest control time was " <<
				# 	latest_control_time_.nanoseconds() << ", control timeout was " <<
				# 	control_timeout_.nanoseconds() << "\n");
				pass

			for controlInd in range(len(StateMembers.TWIST)):
				if self.control_update_vector[controlInd]:
					self.control_acceleration[controlInd] = self.computeControlAcceleration(
						self.state(controlInd + POSITION_V_OFFSET),
						0.0 if timed_out else self.latest_control[controlInd],
						self._acceleration_limits[controlInd], self._acceleration_gains[controlInd],
						self._deceleration_limits[controlInd], self._deceleration_gains[controlInd]
					)

"""
	

	/**
	 * @brief Timeout value, in seconds, after which a control is considered stale
	 */
	rclcpp::Duration control_timeout_;

	/**
	 * @brief Tracks the time the filter was last updated using a measurement.
	 *
	 * This value is used to monitor sensor readings with respect to the
	 * sensorTimeout_. We also use it to compute the time delta values for our
	 * prediction step.
	 */
	rclcpp::Time last_measurement_time_;

	/**
	 * @brief The time of reception of the most recent control term
	 */
	rclcpp::Time latest_control_time_;

	/**
	 * @brief The updates to the filter - both predict and correct - are driven by
	 * measurements. If we get a gap in measurements for some reason, we want the
	 * filter to continue estimating. When this gap occurs, as specified by this
	 * timeout, we will continue to call predict() at the filter's frequency.
	 */
	rclcpp::Duration sensor_timeout_;

	/**
	 * @brief Used for outputting debug messages
	 */
	std::ostream * debug_stream_;

	/**
	 * @brief Gains applied to acceleration derived from control term
	 */
	std::vector<double> acceleration_gains_;

	/**
	 * @brief Caps the acceleration we apply from control input
	 */
	std::vector<double> acceleration_limits_;

	/**
	 * @brief Gains applied to deceleration derived from control term
	 */
	std::vector<double> deceleration_gains_;

	/**
	 * @brief Caps the deceleration we apply from control input
	 */
	std::vector<double> deceleration_limits_;

	/**
	 * @brief Which control variables are being used (e.g., not every vehicle is
	 * controllable in Y or Z)
	 */
	std::vector<bool> control_update_vector_;

	/**
	 * @brief Variable that gets updated every time we process a measurement and
	 * we have a valid control
	 */
	Eigen::VectorXd control_acceleration_;

	/**
	 * @brief Latest control term
	 */
	Eigen::VectorXd latest_control_;

	/**
	 * @brief Holds the last predicted state of the filter
	 */
	Eigen::VectorXd predicted_state_;

	/**
	 * @brief This is the robot's state vector, which is what we are trying to
	 * filter. The values in this vector are what get reported by the node.
	 */
	Eigen::VectorXd state_;

	/**
	 * @brief Covariance matrices can be incredibly unstable. We can add a small
	 * value to it at each iteration to help maintain its positive-definite
	 * property.
	 */
	Eigen::MatrixXd covariance_epsilon_;

	/**
	 * @brief Gets updated when useDynamicProcessNoise_ is true
	 */
	Eigen::MatrixXd dynamic_process_noise_covariance_;

	/**
	 * @brief This matrix stores the total error in our position estimate (the
	 * state_ variable).
	 */
	Eigen::MatrixXd estimate_error_covariance_;

	/**
	 * @brief We need the identity for a few operations. Better to store it.
	 */
	Eigen::MatrixXd identity_;

	/**
	 * @brief As we move through the world, we follow a predict/update cycle. If
	 * one were to imagine a scenario where all we did was make predictions
	 * without correcting, the error in our position estimate would grow without
	 * bound. This error is stored in the stateEstimateCovariance_ matrix.
	 * However, this matrix doesn't answer the question of *how much* our error
	 * should grow for each time step. That's where the processNoiseCovariance
	 * matrix comes in. When we make a prediction using the transfer function, we
	 * add this matrix (times delta_t) to the state estimate covariance matrix.
	 */
	Eigen::MatrixXd process_noise_covariance_;

	/**
	 * @brief The Kalman filter transfer function
	 *
	 * Kalman filters and extended Kalman filters project the current state
	 * forward in time. This is the "predict" part of the predict/correct cycle. A
	 * Kalman filter has a (typically constant) matrix A that defines  how to turn
	 * the current state, x, into the predicted next state. For an EKF, this
	 * matrix becomes a function f(x). However, this function can still be
	 * expressed as a matrix to make the math a little cleaner, which is what we
	 * do here. Technically, each row in the matrix is actually a function. Some
	 * rows will contain many trigonometric functions, which are of course
	 * non-linear. In any case, you can think of this as the 'A' matrix in the
	 * Kalman filter formulation.
	 */
	Eigen::MatrixXd transfer_function_;

	/**
	 * @brief The Kalman filter transfer function Jacobian
	 *
	 * The transfer function is allowed to be non-linear in an EKF, but for
	 * propagating (predicting) the covariance matrix, we need to linearize it
	 * about the current mean (i.e., state). This is done via a Jacobian, which
	 * calculates partial derivatives of each row of the transfer function matrix
	 * with respect to each state variable.
	 */
	Eigen::MatrixXd transfer_function_jacobian_;
"""