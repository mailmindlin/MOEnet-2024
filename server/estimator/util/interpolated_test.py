from unittest import TestCase
from .interpolated import InterpolatingBuffer

def lerp(a: float, b: float, c: float):
    if c < 0:
        return a
    if c > 1:
        return b
    return (b - a) * c + a
    

class TestInterpolate(TestCase):
    def test_lerp(self):
        buffer: InterpolatingBuffer[float, float, float] = InterpolatingBuffer(10, lerp)
        self.assertEqual(len(buffer), 0)
        self.assertIsNone(buffer.get(1))

        buffer.add(1, 1)
        self.assertEqual(len(buffer), 1)
        self.assertEqual(buffer.get(1), 1)
        self.assertEqual(buffer.get(2), 1)
        self.assertEqual(buffer.get(0), 1)

        buffer.add(2, 2)
        self.assertEqual(len(buffer), 2)
        self.assertEqual(buffer.get(0), 1)
        self.assertEqual(buffer.get(1), 1)
        self.assertEqual(buffer.get(1.5), 1.5)
        self.assertEqual(buffer.get(2), 2)
        self.assertEqual(buffer.get(3), 2)

        buffer.add(3, 1)
        self.assertEqual(len(buffer), 3)
        self.assertEqual(buffer.get(0), 1)
        self.assertEqual(buffer.get(1), 1)
        self.assertEqual(buffer.get(1.5), 1.5)
        self.assertEqual(buffer.get(2), 2)
        self.assertEqual(buffer.get(2.5), 1.5)
        self.assertEqual(buffer.get(3), 1)

        # Test cleanup
        buffer.add(15, 0)
        self.assertEqual(len(buffer), 1)
        
    def test_tracking(self):
        buffer: InterpolatingBuffer[float, float, float] = InterpolatingBuffer(10, lerp)
        ks = [0,1,2,3]
        ts = [buffer.track(k) for k in ks]

        self.assertEqual(len(buffer), 0)
        for t in ts:
            self.assertTrue(t.is_fresh)
            self.assertFalse(t.is_static)
            self.assertIsNone(t.current)
        
        buffer.add(1, 1)
        self.assertEqual(len(buffer), 1)
        for t in ts:
            self.assertFalse(t.is_fresh)
            self.assertIsNone(t.current)
        for t in ts:
            t.refresh()
            self.assertEqual(t.current, 1)
            self.assertTrue(t.is_fresh)
        
        buffer.add(3, 2)
        self.assertEqual(len(buffer), 2)
        # Don't auto-refresh
        # Points 0, 1 don't change
        for i,t in enumerate(ts[:2]):
            self.assertTrue(t.is_fresh, f"Tracker {i} is fresh")
            self.assertEqual(t.current, 1)
        # Points 2, 3 change
        for t in ts[2:]:
            self.assertFalse(t.is_fresh)
            self.assertEqual(t.current, 1)
        # Refresh updates value
        for k,t in zip(ks,ts):
            t.refresh()
            self.assertEqual(t.current, buffer.get(k))
