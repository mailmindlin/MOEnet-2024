from unittest import TestCase
from logging import getLogger
from worker_srv import WorkerManager, CameraId

class TestManager(TestCase):
	def test_apriltags(self):
		log = getLogger()
		mgr = WorkerManager(log, None, None)
		assert mgr._resolve_apriltag(CameraId(0, 'test'), None) is None