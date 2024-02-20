from unittest import TestCase
from logging import getLogger
from .controller import WorkerManager
from typedef.cfg import LocalConfig
from .resolver import CameraId

class TestManager(TestCase):
	def test_apriltags(self):
		log = getLogger()
		mgr = WorkerManager(log, LocalConfig(), None)
		assert mgr._resolve_apriltag(CameraId(0, 'test'), None) is None