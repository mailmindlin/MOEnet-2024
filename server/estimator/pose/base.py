from typing import Literal, overload, TYPE_CHECKING, Any
from numpy.typing import NDArray, ArrayLike
import numpy as np
from util.timestamp import Timestamp
from datetime import timedelta
from util.clock import Clock
from enum import IntFlag, auto, Flag
from abc import ABC, abstractmethod, abstractproperty
from contextlib import contextmanager
import logging
from . import angles
from .idx import Slicable

if TYPE_CHECKING:
	from .filter import DataSource

type Vec[N: int] = np.ndarray[tuple[N], np.dtype[np.floating]]
type Mat[M: int, N: int] = np.ndarray[tuple[M, N], np.dtype[np.floating]]

def block_idxs(idxs: list[int] | IntFlag):
	if isinstance(idxs, IntFlag):
		_idxs = np.array(list(idxs), dtype=int)
	else:
		_idxs = np.asanyarray(idxs, dtype=int)
	# Check if consecutive
	if len(_idxs) == 1:
		idx: int = _idxs[0]
		return (idx, idx)
	
	if np.all(np.ediff1d(_idxs) == 1):
		r = range(_idxs[0], _idxs[-1] + 1)
		return (r, r)
	raise ValueError()

def block[T](base: np.ndarray[T] | ArrayLike, idxs: list[int] | IntFlag) -> np.ndarray[T]:
	if isinstance(idxs, IntFlag):
		idxs = np.array(list(idxs), dtype=int)
	
	if base is not None:
		return base[idxs, :][:, idxs]
	raise NotImplemented
	# return base[idxs, :][:, idxs]
 


class StateMembers(IntFlag):
	_ignore_ = [ 'POS_LIN', 'POS_ANG', 'POSE', 'VEL_LIN', 'VEL_ANG', 'TWIST', 'ACC_LIN', 'idxs' ]
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
		return np.log2(int(self))

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
	stamp: Timestamp
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

	measurement: Vec[int]
	"The measurement and its associated covariance"
	covariance: Mat[int, int]

	def __init__(self, ts: Timestamp, source: 'DataSource', *, update_vector: StateMembers = StateMembers.NONE) -> None:
		self.stamp = ts
		self.source = source
		self.update_vector = update_vector
		self.measurement = np.zeros(15, dtype=float)
		self.covariance = np.zeros((15, 15), dtype=float)
		self.mahalanobis_threshold = None

	def measure(self, idxs: StateMembers, value: float | Vec[...], cov: float | Vec[int] | None = None):
		self.measurement[idxs.idxs()] = value
		if cov is not None:
			cov_idxs = np.diag_indices(15)[idxs.idxs()]
			self.covariance[cov_idxs] = cov
	
	def copy_covariance(self, idxs: StateMembers, cov_src: np.ndarray[float]):
		pass

	@property
	def mean_dense(self) -> Vec[Literal[15]]:
		return self.measurement
	@property
	def covariance_dense(self) -> Mat[Literal[15], Literal[15]]:
		return self.covariance

type S = Literal[15]

class FilterBase:
	debug: bool
	process_noise_covariance: Mat[S, S]
	"Gets the filter's process noise covariance"

	dynamic_process_noise_covariance: Mat[S, S]
	def __init__(self, log: logging.Logger, clock: Clock):
		self.log = log
		self.debug = False
		self.is_initialized = False
		"True if we've received our first measurement, false otherwise"
		self.state_len = 15
		self.state: Vec[S] = np.zeros((self.state_len), dtype=float)
		"Current state vector"
		self.estimate_error_covariance: Mat[S, S] = np.zeros((15, 15))
		"The estimated error covariance"
		self.predicted_state: Mat[S, S] = np.zeros((15, 15))
		"The filter's predicted state, i.e., the state estimate before correct() is called."
		self.use_control = False
		"Whether or not we apply the control term"
		self.use_dynamic_process_noise_covariance = False
		"""
		If true, uses the robot's vehicle state and the static process noise
		covariance matrix to generate a dynamic process noise covariance matrix"""

		self.clock = clock
		self.last_measurement_time = Timestamp.invalid(clock)
		"Gets the most recent measurement time"
		self.control_time = Timestamp.invalid(clock)
		"The time at which the control term was issued"
		self.sensor_timeout = timedelta(0)
		"Gets the sensor timeout value"
	
	@abstractmethod
	def reset(self):
		"Resets filter to its unintialized state"
		...

	def computeDynamicProcessNoiseCovariance(self, state: Vec[S]):
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

		twist_idxs = block_idxs(StateMembers.TWIST)
		self.dynamic_process_noise_covariance[twist_idxs] = velocity_matrix @ self.process_noise_covariance[twist_idxs] @ velocity_matrix.T
	
	@contextmanager
	def debug_method(self, *args):
		self.log.info("Start method")
		yield
		self.log.info("Exit method")
	
	def correct(self, measurement: Measurement):
		"""
		Carries out the correct step in the predict/update cycle. This
		method must be implemented by subclasses.
		@param[in] measurement - The measurement to fuse with the state estimate
		"""
		pass

	@property
	@abstractmethod
	def control(self) -> np.floating[T]:
		"The control vector currently being used"
		...
	
	# @property
	# @abstractmethod
	# def control_time(self) -> Timestamp:
	# 	...

	def getState(self) -> np.ndarray[float, S]:
		"Gets the filter state"
		pass

	def validateDelta(self, delta: timedelta):
		"Ensures a given time delta is valid (helps with bag file playback"
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

	@abstractmethod
	def predict(self, reference_time: Timestamp, delta: timedelta):
		"""
		Carries out the predict step in the predict/update cycle.

		Projects the state and error matrices forward using a model of the
		vehicle's motion. This method must be implemented by subclasses.

		@param[in] reference_time - The time at which the prediction is being made
		@param[in] delta - The time step over which to predict.
		"""
		pass

	def processMeasurement(self, measurement: Measurement):
		"""
		Does some final preprocessing, carries out the predict/update cycle
		@param[in] measurement - The measurement object to fuse into the filter
		"""
		with self.debug_method(measurement.source.name):
			delta = timedelta(0)

			# If we've had a previous reading, then go through the predict/update
			# cycle. Otherwise, set our state and covariance to whatever we get
			# from this measurement.
			if self.is_initialized:
				# Determine how much time has passed since our last measurement
				delta = measurement.stamp - self.last_measurement_time

				self.log.debug("Filter is already initialized. Carrying out predict/correct loop...")
				self.log.debug("Measurement time is %s, last measurement time is %s, delta is %s", measurement.stamp.as_seconds(), self.last_measurement_time.as_seconds(), delta.total_seconds())

				# Only want to carry out a prediction if it's
				# forward in time. Otherwise, just correct.
				if delta.total_seconds() > 0:
					self.validateDelta(delta)
					self.predict(measurement.stamp, delta)

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

				self.is_initialized = True

			if delta.total_seconds() > 0:
				# Update the last measurement and update time.
				# The measurement time is based on the time stamp of the
				# measurement, whereas the update time is based on this
				# node's current ROS time. The update time is used to
				# determine if we have a sensor timeout, whereas the
				# measurement time is used to calculate time deltas for
				# prediction and correction.
				self.last_measurement_time = measurement.stamp

	def set_control(self, control: Vec[S], control_time: Timestamp):
		"""
		Sets the most recent control term
		@param[in] control - The control term to be applied
		@param[in] control_time - The time at which the control in question was
		"""
		self.control = control
		self.control_time = control_time

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