from datetime import timedelta
import logging
from unittest import TestCase
import dataclasses

from util.timestamp import Timestamp

from .replay import ReplayFilter, ReplayableFilter
from .cascade import StaticValue, PushValue
from .cascade_replay import CascadingReplayFilter

@dataclasses.dataclass(order=True)
class Measurement:
	ts: Timestamp
	x: float
	dx: float

@dataclasses.dataclass
class State:
	ts: Timestamp
	x: float
	dx: float

class LinearFilter(ReplayableFilter[Measurement, State]):
	def __init__(self) -> None:
		super().__init__()
		self.state = State(Timestamp.invalid(), 0, 0)
	
	@property
	def last_measurement_ts(self):
		return self.state.ts
	
	@last_measurement_ts.setter
	def last_measurement_ts(self, value: Timestamp):
		self.state.ts = value
	
	def snapshot(self) -> State:
		return dataclasses.replace(self.state)
	
	def restore(self, state: State):
		self.state = dataclasses.replace(state)
	
	def observe(self, measurement: Measurement):
		self.state.x = measurement.x
		self.state.dx = measurement.dx
		self.state.ts = measurement.ts
	
	def predict(self, now: Timestamp, delta: timedelta):
		self.state.x += self.state.dx * delta.total_seconds()
		self.state.ts = now

class TestReplay(TestCase):
	def test_baseline(self):
		filter = LinearFilter()
		filter.observe(Measurement(Timestamp(0), 1, 1))
		self.assertEqual(filter.last_measurement_ts, Timestamp(0))
		self.assertEqual(filter.state.x, 1)

		filter.predict(Timestamp(1e9), timedelta(seconds=1))
		self.assertEqual(filter.last_measurement_ts, Timestamp(1e9))
		self.assertEqual(filter.state.x, 2)

		filter.observe(Measurement(Timestamp(1e9), 3, 4))
		self.assertEqual(filter.last_measurement_ts, Timestamp(1e9))
		self.assertEqual(filter.state.x, 3)

		filter.predict(Timestamp(2e9), timedelta(seconds=1))
		self.assertEqual(filter.last_measurement_ts, Timestamp(2e9))
		self.assertEqual(filter.state.x, 7)
	
	def test_inorder(self):
		log = logging.getLogger("filter")
		log.setLevel(logging.DEBUG)
		h = logging.StreamHandler()
		h.setLevel(logging.DEBUG)
		log.addHandler(h)
		log.debug("Hello world")
		filter = LinearFilter()
		rf = ReplayFilter(filter, timedelta(seconds=10), log=log, smooth_lagged_data=True, predict_to_current_time=True)
		rf.observe(Measurement(Timestamp(0), 1, 1))
		# self.assertFalse(filter.is_initialized)

		rf.predict(Timestamp(1e9))
		self.assertEqual(filter.last_measurement_ts, Timestamp(1e9))
		self.assertEqual(filter.state.x, 2)

		rf.observe(Measurement(Timestamp(1e9), 3, 4))
		# Not processed
		self.assertEqual(filter.last_measurement_ts, Timestamp(1e9))
		self.assertEqual(filter.state.x, 2)

		rf.predict(Timestamp(2e9))
		self.assertEqual(filter.last_measurement_ts, Timestamp(2e9))
		self.assertEqual(filter.state.x, 7)
	
	def test_replay(self):
		log = logging.getLogger("filter")

		filter = LinearFilter()
		rf = ReplayFilter(filter, timedelta(seconds=10), log=log, smooth_lagged_data=True, predict_to_current_time=True)

		with self.assertNoLogs(log, logging.INFO + 1):
			rf.observe(Measurement(Timestamp(0e9), 1, 1))
			rf.observe(Measurement(Timestamp(1e9), 3, 4))
			rf.predict(Timestamp(3e9))
		self.assertEqual(filter.last_measurement_ts, Timestamp(3e9))
		self.assertEqual(filter.state.x, 11)


		with self.assertNoLogs(log, logging.INFO + 1):
			rf.observe(Measurement(Timestamp(2e9), 1, 1))
			rf.predict(Timestamp(4e9))
		self.assertEqual(filter.last_measurement_ts, Timestamp(4e9))
		self.assertEqual(filter.state.x, 3)


class TestCascade(TestCase):
	def test_inorder(self):
		log = logging.getLogger("filter")
		filter = LinearFilter()
		cf = CascadingReplayFilter(filter, timedelta(seconds=10), log=log, smooth_lagged_data=True, predict_to_current_time=True)

		cf.observe(Measurement(Timestamp(0), 1, 1))

		cf.predict(Timestamp(1e9))
		self.assertEqual(filter.last_measurement_ts, Timestamp(1e9))
		self.assertEqual(filter.state.x, 2)

		cf.observe(Measurement(Timestamp(1e9), 3, 4))
		# Not processed
		self.assertEqual(filter.last_measurement_ts, Timestamp(1e9))
		self.assertEqual(filter.state.x, 2)

		cf.predict(Timestamp(2e9))
		self.assertEqual(filter.last_measurement_ts, Timestamp(2e9))
		self.assertEqual(filter.state.x, 7)
	
	def test_replay(self):
		log = logging.getLogger("filter")
		filter = LinearFilter()
		cf = CascadingReplayFilter(filter, timedelta(seconds=10), log=log, smooth_lagged_data=True, predict_to_current_time=True)

		with self.assertNoLogs(log, logging.INFO + 1):
			cf.observe(Measurement(Timestamp(0e9), 1, 1))
			cf.observe(Measurement(Timestamp(1e9), 3, 4))
			cf.predict(Timestamp(3e9))
		self.assertEqual(filter.last_measurement_ts, Timestamp(3e9))
		self.assertEqual(filter.state.x, 11)


		with self.assertNoLogs(log, logging.INFO + 1):
			cf.observe(Measurement(Timestamp(2e9), 1, 1))
			cf.predict(Timestamp(4e9))
		self.assertEqual(filter.last_measurement_ts, Timestamp(4e9))
		self.assertEqual(filter.state.x, 3)
	
	def test_cascade(self):
		log = logging.getLogger("filter")

		filter = LinearFilter()
		cf = CascadingReplayFilter(filter, timedelta(seconds=10), log=log, smooth_lagged_data=True, predict_to_current_time=True)

		t_dx = PushValue(4.0)

		with self.assertNoLogs(log, logging.INFO + 1):
			cf.observe(Measurement(Timestamp(0e9), 1, 1))
			cf.observe(t_dx.map(lambda dx: Measurement(Timestamp(1e9), 3, dx)))
			cf.predict(Timestamp(3e9))
		
		self.assertEqual(filter.last_measurement_ts, Timestamp(3e9))
		self.assertEqual(filter.state.x, 3 + 4*2)


		with self.assertNoLogs(log, logging.INFO + 1):
			t_dx.update(5.0) # Trigger cascade
			cf.predict(Timestamp(3e9)) # recalculate
		
		self.assertEqual(filter.last_measurement_ts, Timestamp(3e9))
		self.assertEqual(filter.state.x, 3 + 5 * 2)