from unittest import TestCase
from .cascade import Tracked, StaticValue, PushValue

class TestStatic(TestCase):
	def test_simple(self):
		t = StaticValue(5.0)

		self.assertTrue(t.is_fresh)
		self.assertTrue(t.is_static)
		self.assertEqual(t.value, 5.0)
		self.assertEqual(t.refresh(), t)
	
	def test_map(self):
		t = StaticValue(5.0)
		r = t.map(lambda x: x * x)

		self.assertTrue(r.is_fresh)
		self.assertTrue(r.is_static)
		self.assertEqual(r.value, 25.0)
		self.assertEqual(r.refresh(), r)

class TestDerive(TestCase):
	def test_map(self):
		a = PushValue(5)
		assert a.is_fresh
		assert not a.is_static
		assert a.value == 5

		b = a.map(lambda x: x * x)
		assert b.is_fresh
		assert not b.is_static
		assert b.value == 25

		a.value_next = 6
		assert not b.is_fresh
		assert not a.is_fresh
		# Check no auto-refresh
		assert a.value == 5
		assert b.value == 25

		a = a.refresh()
		assert a.value == 6
		assert a.is_fresh
		assert b.value == 25
		assert not b.is_fresh

		b = b.refresh()
		assert b.value == 36
		assert b.is_fresh
