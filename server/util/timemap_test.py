from unittest import TestCase
from .clock import MonoClock, WallClock, FixedOffsetClock
from .timemap import TimeMap, FixedOffsetMapper, IdentityTimeMapper, OffsetClockMapper

class TimeMapperTest(TestCase):
	def test_identity(self):
		c = MonoClock()
		m = IdentityTimeMapper(c)
		t0 = c.now()
		assert t0.clock == c
		t1 = m.a_to_b(t0)
		assert t0 == t1
		assert t1.clock == c
	
	def test_fixed(self):
		c_m = MonoClock()
		c_w = WallClock()

		fom = FixedOffsetMapper(c_m, c_w, 100)
		t_m = c_m.now()
		assert t_m.clock == c_m
		t_w = fom.a_to_b(t_m)
		assert t_w.clock == c_w
		assert int(t_m) + 100 == int(t_w)
	

class TimeMapTest(TestCase):
	def test_search_identity(self):
		c_m = MonoClock()
		map = TimeMap()
		conv = map.get_conversion(c_m, c_m)
		assert conv is not None
		assert conv.clock_a == c_m
		assert conv.clock_b == c_m

		t0 = c_m.now()
		assert t0.clock == c_m
		t1 = conv.a_to_b(t0)
		assert t1.clock == c_m
		assert t0 == t1
	
	def test_search_simple(self):
		c_m = MonoClock()
		c_w = WallClock()
		map = TimeMap(
			FixedOffsetMapper(c_m, c_w, 100)
		)
		
		conv = map.get_conversion(c_m, c_w)
		assert conv is not None
		assert conv.clock_a == c_m
		assert conv.clock_b == c_w
	
	def test_search_2(self):
		c0 = MonoClock()
		c1 = FixedOffsetClock(c0, 100)
		c2 = FixedOffsetClock(c1, 200)
		map = TimeMap(
			OffsetClockMapper(c1),
			OffsetClockMapper(c2),
		)
		
		conv = map.get_conversion(c0, c2)
		assert conv is not None
		assert conv.clock_a == c0
		assert conv.clock_b == c2
		
		t0 = c0.now()
		assert t0.clock == c0
		t2 = conv.a_to_b(t0)
		assert t2.clock == c2
		assert int(t0) + 300 == int(t2)
	
	def test_search_rev(self):
		c0 = MonoClock()
		c1 = FixedOffsetClock(c0, 100)
		c2 = FixedOffsetClock(c1, 200)
		map = TimeMap(
			OffsetClockMapper(c1),
			OffsetClockMapper(c2),
		)
		
		conv = map.get_conversion(c2, c0)
		assert conv is not None
		assert conv.clock_a == c2
		assert conv.clock_b == c0
		
		t2 = c2.now()
		assert t2.clock == c2
		t0 = conv.a_to_b(t2)
		assert t0.clock == c0
		assert int(t0) + 300 == int(t2)
	
	def test_context(self):
		c0 = MonoClock()
		c1 = FixedOffsetClock(c0, 100)

		with TimeMap(OffsetClockMapper(c1)):
			conv = TimeMap.default.get_conversion(c0, c1)
			assert conv is not None
	
	def test_context2(self):
		c0 = MonoClock()
		c1 = FixedOffsetClock(c0, 100)
		c2 = FixedOffsetClock(c1, 200)

		assert not TimeMap.default.get_conversion(c0, c1)
		assert not TimeMap.default.get_conversion(c0, c2)
		
		with OffsetClockMapper(c1):
			assert TimeMap.default.get_conversion(c0, c1)
			assert not TimeMap.default.get_conversion(c0, c2)

			with OffsetClockMapper(c2):
				assert TimeMap.default.get_conversion(c0, c1)
				assert TimeMap.default.get_conversion(c0, c2)