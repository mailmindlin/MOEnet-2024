from unittest import TestCase
from clock import MonoClock, WallClock

class SingletonTest(TestCase):
	def test_mono(self):
		"Check that MonoClock is singleton"
		c0 = MonoClock()
		c1 = MonoClock()
		assert c0 is c1
		assert c0 == c1
	
	def test_monoclock_monotonic(self):
		c = MonoClock()

		t0 = c.now()
		t1 = c.now()

		assert t1 >= t0

	def test_wall(self):
		"Check that WallClock is singleton"
		c0 = WallClock()
		c1 = WallClock()
		assert c0 is c1
		assert c0 == c1