from unittest import TestCase
from .clock import MonoClock, WallClock
from .decorators import Singleton

class SingletonTest(TestCase):
	def test_identity(self):
		class Foo:
			pass
		class Bar(Singleton):
			pass

		assert Foo() is not Foo()
		assert Bar() is Bar()