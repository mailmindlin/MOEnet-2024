from datetime import timedelta
import numpy as np
from typing import Literal, TypeVar

from server.util.timestamp import Timestamp
from .base import FilterBase, Measurement, StateMembers, ControlMembers
from . import angles

M = TypeVar('M', bound=int)
S = TypeVar('S', bound=int)

def sample_cov(cov: np.ndarray, idxs: list[int]) -> np.ndarray:
	return cov[idxs, :][:, idxs]

class EKF(FilterBase):
	def correct(self, measurement: Measurement):
		#     FB_DEBUG(
		# "---------------------- Ekf::correct ----------------------\n" <<
		#   "State is:\n" <<
		#   state_ <<
		#   "\n"
		#   "Topic is:\n" <<
		#   measurement.topic_name_ <<
		#   "\n"
		#   "Measurement is:\n" <<
		#   measurement.measurement_ <<
		#   "\n"
		#   "Measurement topic name is:\n" <<
		#   measurement.topic_name_ <<
		#   "\n\n"
		#   "Measurement covariance is:\n" <<
		#   measurement.covariance_ << "\n");
		

		# We don't want to update everything, so we need to build matrices that only
		# update the measured parts of our state vector. Throughout prediction and
		# correction, we attempt to maximize efficiency in Eigen.

		# First, determine how many state vector values we're updating
		update_idxs: np.ndarray[int, M] = np.array(list(measurement.update_vector), dtype=int)
		# Handle NaN and inf
		valid = np.isfinite(measurement.measurement[update_idxs])
		if not np.all(valid):
			self.log.debug("Values at indices %s were invalid", [StateMembers(i) for i in update_idxs[~valid].tolist()])
			update_idxs = update_idxs[valid]
		
		self.log.debug("Update indices are: %s", [StateMembers(i) for i in update_idxs.tolist()])
		
		update_len = len(update_idxs)
		state_len = np.shape(self.state)[0]

		# Now build the sub-matrices from the full-sized matrices
		# x (in most literature)
		state_subset = self.state[update_idxs]
		# z
		measurement_subset = measurement.measurement[update_idxs]
		# R
		measurement_covariance_subset = sample_cov(measurement.covariance, update_idxs)
		cov_diag = np.diagonal(measurement_covariance_subset)
		# Handle negative (read: bad) covariances in the measurement. Rather
		# than exclude the measurement or make up a covariance, just take
		# the absolute value.
		if self.debug and np.any(cov_diag < 0):
			self.log.warning("Negative covariance for indices")
		cov_diag = np.abs(cov_diag)
		# If the measurement variance for a given variable is very
		# near 0 (as in e-50 or so) and the variance for that
		# variable in the covariance matrix is also near zero, then
		# the Kalman gain computation will blow up. Really, no
		# measurement can be completely without error, so add a small
		# amount in that case.
		if self.debug and np.any(cov_diag < 1e-9):
			self.log.warning("measurement had very small error covariance indices")
		cov_diag[cov_diag < 1e-9] = 1e-9
		np.fill_diagonal(measurement_covariance_subset, cov_diag)

		# H
		state_to_measurement_subset = np.zeros((update_len, state_len), dtype=float)
		# The state-to-measurement function, h, will now be a measurement_size x
		# full_state_size matrix, with ones in the (i, i) locations of the values to
		# be updated
		for i, idx in enumerate(update_idxs.tolist()):
			state_to_measurement_subset[i, idx] = 1
		

		# FB_DEBUG(
		# 	"Current state subset is:\n" <<
		# 	state_subset << "\nMeasurement subset is:\n" <<
		# 	measurement_subset << "\nMeasurement covariance subset is:\n" <<
		# 	measurement_covariance_subset <<
		# 	"\nState-to-measurement subset is:\n" <<
		# 	state_to_measurement_subset << "\n");

		# (1) Compute the Kalman gain: K = (PH') / (HPH' + R)
		pht = self.estimate_error_covariance @ state_to_measurement_subset.transpose()
		hphr_inv = np.linalg.inv(state_to_measurement_subset @ pht + measurement_covariance_subset)
		kalman_gain_subset: np.ndarray[float] = pht @ hphr_inv

		# z - Hx
		innovation_subset = (measurement_subset - state_subset)

		# Wrap angles in the innovation
		_, angles_idxs, _ = np.intersect1d(update_idxs, np.array(list(StateMembers.VEL_ANG), dtype=int), assume_unique=True, return_indices=True)
		if len(angles_idxs) > 0:
			innovation_subset[angles_idxs] = angles.normalize_angle(innovation_subset[angles_idxs])

		# (2) Check Mahalanobis distance between mapped measurement and state.
		if (self.checkMahalanobisThreshold(innovation_subset, hphr_inv, measurement.mahalanobis_threshold)):
			# (3) Apply the gain to the difference between the state and measurement: x
			# = x + K(z - Hx)
			self.state += kalman_gain_subset @ innovation_subset

			# (4) Update the estimate error covariance using the Joseph form: (I -
			# KH)P(I - KH)' + KRK'
			gain_residual = np.eye((15, 15), dtype=float) - (kalman_gain_subset @ state_to_measurement_subset)
			self.estimate_error_covariance = gain_residual @ self.estimate_error_covariance @ gain_residual.transpose()
			self.estimate_error_covariance += kalman_gain_subset @ measurement_covariance_subset @ kalman_gain_subset.transpose()

			# Handle wrapping of angles
			self.wrapStateAngles()

			# self.log.debug(
			# "Kalman gain subset is:\n" <<
			# 	kalman_gain_subset << "\nInnovation is:\n" <<
			# 	innovation_subset << "\nCorrected full state is:\n" <<
			# 	state_ << "\nCorrected full estimate error covariance is:\n" <<
			# 	estimate_error_covariance_ <<
			# 	"\n\n---------------------- /Ekf::correct ----------------------\n")
		return
	
	def predict(self, reference_time: Timestamp, delta: timedelta):
		delta_sec = delta.total_seconds()

		# FB_DEBUG(
		# 	"---------------------- Ekf::predict ----------------------\n" <<
		# 	"delta is " << filter_utilities::toSec(delta) << "\n" <<
		# 	"state is " << state_ << "\n");

		roll = self.state[StateMembers.Roll.idx()]
		pitch = self.state[StateMembers.Pitch.idx()]
		yaw = self.state[StateMembers.Yaw.idx()]
		x_vel = self.state[StateMembers.Vx.idx()]
		y_vel = self.state[StateMembers.Vy.idx()]
		z_vel = self.state[StateMembers.Vz.idx()]
		pitch_vel = self.state[StateMembers.Vpitch.idx()]
		yaw_vel = self.state[StateMembers.Vyaw.idx()]
		x_acc = self.state[StateMembers.Ax.idx()]
		y_acc = self.state[StateMembers.Ay.idx()]
		z_acc = self.state[StateMembers.Az.idx()]

		# We'll need these trig calculations a lot.
		sp = np.sin(pitch)
		cp = np.cos(pitch)
		cpi = 1.0 / cp
		tp = sp * cpi

		sr = np.sin(roll)
		cr = np.cos(roll)

		sy = np.sin(yaw)
		cy = np.cos(yaw)

		self.prepareControl(reference_time, delta)

		# Prepare the transfer function
		def set_tfj(src: StateMembers, dst: StateMembers, val: float):
			self.transfer_function[src.idx(), dst.idx()] = val
		
		x_vxyz = np.array([
			cy * cp,
			cy * sp * sr - sy * cr,
			cy * sp * cr + sy * sr
		]) * delta_sec
		self.transfer_function[StateMembers.X.idx(), StateMembers.VEL_LIN.idxs()] = x_vxyz
		self.transfer_function[StateMembers.X.idx(), StateMembers.ACC_LIN.idxs()] = 0.5 * x_vxyz * delta_sec
		
		y_vxyz = np.array([
			sy * cp,
			sy * sp * sr + cy * cr,
			sy * sp * cr - cy * sr
		]) * delta_sec
		self.transfer_function[StateMembers.Y.idx(), StateMembers.VEL_LIN.idxs()] = y_vxyz
		self.transfer_function[StateMembers.Y.idx(), StateMembers.ACC_LIN.idxs()] = 0.5 * y_vxyz * delta_sec

		z_vxyz = np.array([
			-sp,
			cp * sr,
			cp * cr
		]) * delta_sec
		self.transfer_function[StateMembers.Z.idx(), StateMembers.VEL_LIN.idxs()] = z_vxyz
		self.transfer_function[StateMembers.Z.idx(), StateMembers.ACC_LIN.idxs()] = 0.5 * z_vxyz * delta_sec

		self.transfer_function[StateMembers.Roll.idx(), StateMembers.VEL_ANG.idxs()] = np.array([
			1.0,
			sr * tp,
			cr * tp,
		]) * delta_sec
		transfer_function_(StateMemberPitch, StateMemberVpitch) = cr * delta_sec;
		transfer_function_(StateMemberPitch, StateMemberVyaw) = -sr * delta_sec;
		transfer_function_(StateMemberYaw, StateMemberVpitch) = sr * cpi * delta_sec;
		transfer_function_(StateMemberYaw, StateMemberVyaw) = cr * cpi * delta_sec;
		transfer_function_(StateMemberVx, StateMemberAx) = delta_sec;
		transfer_function_(StateMemberVy, StateMemberAy) = delta_sec;
		transfer_function_(StateMemberVz, StateMemberAz) = delta_sec;

		# Prepare the transfer function Jacobian. This function is analytically
		# derived from the transfer function.
		x_coeff = 0.0
		y_coeff = 0.0
		z_coeff = 0.0
		one_half_at_squared = 0.5 * delta_sec * delta_sec

		y_coeff = cy * sp * cr + sy * sr
		z_coeff = -cy * sp * sr + sy * cr
		dFx_dR = (y_coeff * y_vel + z_coeff * z_vel) * delta_sec + (y_coeff * y_acc + z_coeff * z_acc) * one_half_at_squared
		dFR_dR = 1.0 + (cr * tp * pitch_vel - sr * tp * yaw_vel) * delta_sec

		x_coeff = -cy * sp
		y_coeff = cy * cp * sr
		z_coeff = cy * cp * cr
		dFx_dP = \
			(x_coeff * x_vel + y_coeff * y_vel + z_coeff * z_vel) * delta_sec + \
			(x_coeff * x_acc + y_coeff * y_acc + z_coeff * z_acc) * \
			one_half_at_squared
		dFR_dP = (cpi * cpi * sr * pitch_vel + cpi * cpi * cr * yaw_vel) * delta_sec

		x_coeff = -sy * cp
		y_coeff = -sy * sp * sr - cy * cr
		z_coeff = -sy * sp * cr + cy * sr
		dFx_dY = \
			(x_coeff * x_vel + y_coeff * y_vel + z_coeff * z_vel) * delta_sec + \
			(x_coeff * x_acc + y_coeff * y_acc + z_coeff * z_acc) * \
			one_half_at_squared

		y_coeff = sy * sp * cr - cy * sr
		z_coeff = -sy * sp * sr - cy * cr
		dFy_dR = (y_coeff * y_vel + z_coeff * z_vel) * delta_sec + \
			(y_coeff * y_acc + z_coeff * z_acc) * one_half_at_squared
		dFP_dR = (-sr * pitch_vel - cr * yaw_vel) * delta_sec

		x_coeff = -sy * sp
		y_coeff = sy * cp * sr
		z_coeff = sy * cp * cr
		dFy_dP = \
			(x_coeff * x_vel + y_coeff * y_vel + z_coeff * z_vel) * delta_sec + \
			(x_coeff * x_acc + y_coeff * y_acc + z_coeff * z_acc) * \
			one_half_at_squared

		x_coeff = cy * cp
		y_coeff = cy * sp * sr - sy * cr
		z_coeff = cy * sp * cr + sy * sr
		dFy_dY = \
			(x_coeff * x_vel + y_coeff * y_vel + z_coeff * z_vel) * delta_sec + \
			(x_coeff * x_acc + y_coeff * y_acc + z_coeff * z_acc) * \
			one_half_at_squared

		y_coeff = cp * cr
		z_coeff = -cp * sr
		dFz_dR = (y_coeff * y_vel + z_coeff * z_vel) * delta_sec + \
			(y_coeff * y_acc + z_coeff * z_acc) * one_half_at_squared
		dFY_dR = (cr * cpi * pitch_vel - sr * cpi * yaw_vel) * delta_sec

		x_coeff = -cp
		y_coeff = -sp * sr
		z_coeff = -sp * cr
		dFz_dP = \
			(x_coeff * x_vel + y_coeff * y_vel + z_coeff * z_vel) * delta_sec + \
			(x_coeff * x_acc + y_coeff * y_acc + z_coeff * z_acc) * \
			one_half_at_squared
		dFY_dP = \
			(sr * tp * cpi * pitch_vel + cr * tp * cpi * yaw_vel) * delta_sec

		# Much of the transfer function Jacobian is identical to the transfer
		# function
		self.transfer_function_jacobian = np.copy(self.transfer_function)
		def set_tfj(src: StateMembers, dst: StateMembers, val: float):
			self.transfer_function_jacobian[src.idx(), dst.idx()] = val
		set_tfj(StateMembers.X, StateMembers.Roll, dFx_dR)
		set_tfj(StateMembers.X, StateMembers.Pitch, dFx_dP)
		set_tfj(StateMembers.X, StateMembers.Yaw, dFx_dY)
		set_tfj(StateMembers.Y, StateMembers.Roll, dFy_dR)
		set_tfj(StateMembers.Y, StateMembers.Pitch, dFy_dP)
		set_tfj(StateMembers.Y, StateMembers.Yaw, dFy_dY)
		set_tfj(StateMembers.Z, StateMembers.Roll, dFz_dR)
		set_tfj(StateMembers.Z, StateMembers.Pitch, dFz_dP)
		set_tfj(StateMembers.Roll, StateMembers.Roll, dFR_dR)
		set_tfj(StateMembers.Roll, StateMembers.Pitch, dFR_dP)
		set_tfj(StateMembers.Pitch, StateMembers.Roll, dFP_dR)
		set_tfj(StateMembers.Yaw, StateMembers.Roll, dFY_dR)
		set_tfj(StateMembers.Yaw, StateMembers.Pitch, dFY_dP)

		# FB_DEBUG(
		# 	"Transfer function is:\n" <<
		# 	transfer_function_ << "\nTransfer function Jacobian is:\n" <<
		# 	transfer_function_jacobian_ << "\nProcess noise covariance is:\n" <<
		# 	process_noise_covariance_ << "\nCurrent state is:\n" <<
		# 	state_ << "\n");

		process_noise_covariance = np.copy(self.process_noise_covariance)

		if self.use_dynamic_process_noise_covariance:
			self.computeDynamicProcessNoiseCovariance(self.state)
			process_noise_covariance = np.copy(self.dynamic_process_noise_covariance)

		# (1) Apply control terms, which are actually accelerations
		self.state[StateMembers.VEL_ANG.idxs()] += self.control_acceleration[ControlMembers.VEL_ANG.idxs()] * delta_sec

		self.state[StateMembers.ACC_LIN.idxs()] = np.where(
			self.control_update_vector[ControlMembers.ACC_LIN.idxs()],
			self.control_acceleration[ControlMembers.ACC_LIN.idxs()],
			self.state[StateMembers.ACC_LIN.idxs()]
		)

		# (2) Project the state forward: x = Ax + Bu (really, x = f(x, u))
		self.state = self.transfer_function @ self.state

		# Handle wrapping
		self.wrapStateAngles()

		# FB_DEBUG(
		# 	"Predicted state is:\n" <<
		# 	state_ << "\nCurrent estimate error covariance is:\n" <<
		# 	estimate_error_covariance_ << "\n");

		# (3) Project the error forward: P = J * P * J' + Q
		self.estimate_error_covariance = self.transfer_function_jacobian @ self.estimate_error_covariance @ self.transfer_function_jacobian.transpose()
		self.estimate_error_covariance += delta_sec * self.process_noise_covariance

		self.log.debug("Predicted estimate error covariance is:%s", self.estimate_error_covariance)