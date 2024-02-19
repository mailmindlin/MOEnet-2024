from typing import Generic, TypeVar, Protocol
from datetime import timedelta
from logging import Logger
from collections import deque
from abc import ABC, abstractmethod
from util.timestamp import Timestamp

from .heap import Heap
from .types import HasTimestamp


S = TypeVar('S', bound=HasTimestamp)
"Filter state"
M = TypeVar('M', bound=HasTimestamp)
"Measurement"

class ReplayableFilter(Generic[M, S], ABC):
	last_measurement_ts: Timestamp
	"Timestamp of last processed measurement"
	is_initialized: bool
	sensor_timeout: timedelta
	
	@abstractmethod
	def snapshot(self) -> S:
		"Take a snapshot of this filter's data (should take the timestamp from last_measurement_ts)"
		pass
	@abstractmethod
	def restore(self, state: S):
		"Restore state from a snapshot"
		pass

	def differentiate(self, now: Timestamp):
		pass

	def validate_delta(self, delta: timedelta):
		pass

	@abstractmethod
	def predict(self, now: Timestamp, delta: timedelta):
		pass

	@abstractmethod
	def process_measurement(self, measurement: M):
		pass


def _pop_before(queue: deque[M], cutoff: Timestamp):
	"Pop all entries that happened before `cutoff`"
	popped = 0
	while (len(queue) > 0) and queue[0].ts < cutoff:
		queue.popleft()
		popped += 1
	return popped

def _pop_after(queue: deque[M], cutoff: Timestamp) -> M | None:
	"Pop all entries that happened after `cutoff`"
	last = None
	while (len(queue) > 0) and queue[-1].ts > cutoff:
		last = queue.pop()
	return last


class ReplayFilter(Generic[M, S]):
	"""
	A lot of """
	def __init__(self, log: Logger, filter: ReplayableFilter[M, S]):
		self.log = log
		self._filter = filter
		self._measurement_queue: Heap[M] = Heap()
		self._filter_state_history: deque[S] = deque()
		self._measurement_history: deque[M] = deque()
		"Measurements already processed by the filter, in order of timestamp"
		self.enabled = True
		self.use_control = False
	
	def _clear_expired_history(self, cutoff_time: Timestamp):
		popped_measurements = _pop_before(self._measurement_history, cutoff_time)
		popped_states = _pop_before(self._filter_state_history, cutoff_time)

		self.log.debug("Popped %s measurements and %s states from their queues", popped_measurements, popped_states)
	
	def clear(self):
		self._measurement_queue.clear()
		self._filter_state_history.clear()
		self._measurement_history.clear()
	
	def observe(self, measurement: M):
		self._measurement_queue.push(measurement)
	
	def revert_to(self, time: Timestamp) -> bool:
		self.log.debug("Requested time was %s to revert", time)
		# Walk back through the queue until we reach a filter state whose time stamp
		# is less than or equal to the requested time. Since every saved state after
		# that time will be overwritten/corrected, we can pop from the queue. If the
		# history is insufficiently short, we just take the oldest state we have.
		last_history_state = _pop_after(self._filter_state_history, time)

		# If the state history is not empty at this point, it means that our history
		# was large enough, and we should revert to the state at the back of the
		# history deque.
		success = False
		if len(self._filter_state_history) > 0:
			success = True
			last_history_state = self._filter_state_history[-1]
		else:
			self.log.debug("Insufficient history to revert to time %s", time)

			if last_history_state:
				self.log.debug("Will revert to oldest state at %s", last_history_state.ts)

		# If we have a valid reversion state, revert
		if last_history_state:
			# Reset filter to the latest state from the queue.
			state = last_history_state
			self._filter.restore(state)
			self.log.debug("Reverted to state with time %s", state.ts)

			# Repeat for measurements, but push every measurement onto the measurement
			# queue as we go
			restored_measurements = 0
			while len(self._measurement_history) > 0 and self._measurement_history[-1].ts > time:
				# Don't need to restore measurements that predate our earliest state time
				measurement = self._measurement_history.pop()
				if state.ts <= measurement.ts:
					self._measurement_queue.push(measurement)
					restored_measurements += 1

			self.log.debug("Restored %s to measurement queue.", restored_measurements)

		return success

	def _snapshot_filter(self):
		state = self._filter.snapshot()
		self._filter_state_history.append(state)
		self.log.debug("Saved state with timestamp %s to history. %s measurements are in the queue.", state.ts, len(self._filter_state_history))
	
	def _integrate_measurements(self, now: Timestamp, smooth_lagged_data: bool = False, predict_to_current_time: bool = True):
		"""
		Processes all measurements in the measurement queue, in temporal order

		@param[in] now - The time at which to carry out integration (the current time)
		"""
		# If we have any measurements in the queue, process them
		if (first_measurement := self._measurement_queue.peek()) is not None:
			# Check if the first measurement we're going to process is older than the
			# filter's last measurement. This means we have received an out-of-sequence
			# message (one with an old timestamp), and we need to revert both the
			# filter state and measurement queue to the first state that preceded the
			# time stamp of our first measurement.
			restored_measurement_count = 0
			if smooth_lagged_data and first_measurement.ts < self._filter.last_measurement_ts:
				# RF_DEBUG(
				# 	"Received a measurement that was " <<
				# 	filter_utilities::toSec(
				# 	filter_.getLastMeasurementTime() -
				# 	first_measurement->time_) <<
				# 	" seconds in the past. Reverting filter state and "
				# 	"measurement queue...");

				original_count = len(self._measurement_queue)
				first_measurement_time = first_measurement.ts
				# revertTo may invalidate first_measurement
				if not self.revert_to(first_measurement_time - timedelta(micros=1)):
					self.log.warning("history interval is too small to revert to time %s", first_measurement_time)
					# ROS_WARN_STREAM_DELAYED_THROTTLE(history_length_,
					#   "Received old measurement for topic " << first_measurement_topic <<
					#   ", but history interval is insufficiently sized. "
					#   "Measurement time is " << std::setprecision(20) <<
					#   first_measurement_time <<
					#   ", current time is " << current_time <<
					#   ", history length is " << history_length_ << ".");
					restored_measurement_count = 0

				restored_measurement_count = len(self._measurement_queue) - original_count

			while (measurement := self._measurement_queue.peek()) is not None:
				# If we've reached a measurement that has a time later than now, it
				# should wait until a future iteration. Since measurements are stored in
				# a priority queue, all remaining measurements will be in the future.
				if now < measurement.ts:
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
				if self.use_control and restored_measurement_count > 0:
					self._filter.set_control(measurement.latest_control, measurement.latest_control_time)
					restored_measurement_count -= 1

				# This will call predict and, if necessary, correct
				self._filter.process_measurement(measurement)

				# Store old states and measurements if we're smoothing
				if smooth_lagged_data:
					# Invariant still holds: measurementHistoryDeque_.back().time_ <
					# measurement_queue_.top().time_
					self._measurement_history.append(measurement)

					# We should only save the filter state once per unique timstamp
					if len(self._measurement_queue) == 0 or self._measurement_queue.peek().ts != self._filter.last_measurement_ts:
						self._snapshot_filter()
		elif self._filter.is_initialized:
			# In the event that we don't get any measurements for a long time,
			# we still need to continue to estimate our state. Therefore, we
			# should project the state forward here.
			last_update_delta = now - self._filter.last_measurement_ts

			# If we get a large delta, then continuously predict until
			if last_update_delta >= self._filter.sensor_timeout:
				predict_to_current_time = True

				self.log.debug("Sensor timeout! Last measurement time was %s, current time is %s, delta is %s", self._filter.last_measurement_ts, now, last_update_delta)
		else:
			self.log.debug("Filter not yet initialized.")

		if self._filter.is_initialized and predict_to_current_time:
			last_update_delta = now - self._filter.last_measurement_ts

			self._filter.validate_delta(last_update_delta)
			self._filter.predict(now, last_update_delta)

			# Update the last measurement time and last update time
			self._filter.last_measurement_ts += last_update_delta

	def _differentiate_measurements(self, now: Timestamp):
		if self._filter.is_initialized:
			self._filter.differentiate(now)
	
	def enqueue_measurement(self, measurement: M):
		self._measurement_queue.push(measurement)
	
	def poll(self, now: Timestamp):
		if self.enabled:
			# Now we'll integrate any measurements we've received if requested,
			# and update angular acceleration.
			self._integrate_measurements(now)
			self._differentiate_measurements(now)
		else:
			# Clear out measurements since we're not currently processing new entries
			self._measurement_queue.clear()

			# Reset last measurement time so we don't get a large time delta on toggle
			if self._filter.is_initialized:
				self._filter.last_measurement_ts = now