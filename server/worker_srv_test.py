from unittest import TestCase
from .worker_srv import WorkerManager, CameraId
from logging import getLogger
from pathlib import Path
from .typedef.cfg import LocalConfig, AprilTagFieldConfig

class TestManager(TestCase):
	def test_apriltags(self):
		log = getLogger()
		mgr = WorkerManager(log, None, None)
		assert mgr._resolve_apriltag(CameraId(0, 'test'), None) is None