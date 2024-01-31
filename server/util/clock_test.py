from unittest import TestCase
from clock import MonoClock, WallClock

class SingletonTest(TestCase):
	def test_mono(self):
		c0 = MonoClock()
		c1 = MonoClock()
		assert c0 is c1
		assert c0 == c1

	def test_wall(self):
		c0 = WallClock()
		c1 = WallClock()
		assert c0 is c1
		assert c0 == c1