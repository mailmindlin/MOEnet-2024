from typing import TYPE_CHECKING
import signal
import logging
from typedef.cfg import LocalConfig, RemoteConfig

class InterruptHandler:
	def __init__(self, callback) -> None:
		self._callback = callback
	def __enter__(self):
		self._prev = signal.signal(signal.SIGINT, self._callback)

	def __exit__(self, *args):
		assert signal.signal(signal.SIGINT, self._prev) is self._callback

class MoeNet:
	def __init__(self, config_path: str, config: LocalConfig):
		if config.log is not None:
			level = config.log.level.upper()
			root = logging.getLogger()
			root.setLevel(level)

		self.log = logging.getLogger("MoeNet")
		self.config_path = config_path
		self.config = config
		self.initial_config = config
		self.log.info('Using config from %s', config_path)

		from comms import Comms, Status
		self.nt = Comms(self, self.config)
		self.nt.tx_status(Status.NOT_READY)
		self.sleeping = False
		self.camera_workers = None

		if self.config.timer == "system":
			from clock import TimeMapper
			self.clock = TimeMapper()
			self.log.info("Selected system timer")
		else:
			try:
				self.log.info("Connecting to NavX timer")
				from clock import NavXTimeMapper
				self.clock = NavXTimeMapper(self.config.timer)
			except:
				self.nt.tx_error("Unable to construct NavX clock")
				raise
	
	def update_config(self, config: RemoteConfig):
		"Apply remote config options"

		self.log.info("Updating config from remote: %", config)

		next_config = self.initial_config.merge(config)
		update_cameras = (next_config.cameras != self.config.cameras) or (next_config.slam != self.config.slam)

		self.config = next_config
		if update_cameras:
			from comms import Status
			self.nt.tx_status(Status.INITIALIZING)
		self.reset(update_cameras)
	
	def build_cameras(self):
		from worker_srv import WorkerManager
		if self.camera_workers is not None:
			self.camera_workers.stop()
			self.camera_workers = None
		
		self.camera_workers = WorkerManager(self.log, self.config, self.config_path)
		self.camera_workers.start()
	
	def reset(self, flush_cameras: bool = True):
		if len(self.config.cameras) == 0:
			self.nt.tx_error("No cameras")
		
		if flush_cameras:
			self.build_cameras()
	
	def poll(self):
		# self.log.debug("Tick start")
		self.nt.update()
		from typedef.worker import MsgPose, MsgDetections

		active = True
		while active:
			active = False
			for i, worker in enumerate(self.camera_workers):
				# self.log.info("Poll worker %d", i)
				for packet in worker.poll():
					# self.log.info("Recv packet %s", repr(packet))
					if isinstance(packet, MsgPose):
						self.nt.tx_pose(packet.pose)
					elif isinstance(packet, MsgDetections):
						self.nt.tx_detections(packet.detections)
					active = True
	
	def run(self):
		import time
		self.reset(True)

		interrupt = False
		def handle_interrupt(*args):
			self.log.info("Exiting (SIGINT)... %s", args)
			nonlocal interrupt
			interrupt = True

		with InterruptHandler(handle_interrupt):
			while not interrupt:
				t0 = time.monotonic_ns()
				if self.poll():
					continue
				t1 = time.monotonic_ns()
				delta = (t1 - t0)
				# Cap at 100Hz
				if delta < 1e7:
					time.sleep((1e7 - delta) / 1e9)
	
	def cleanup(self):
		self.log.info("Cleanup MoeNet")
		if self.camera_workers is not None:
			self.camera_workers.stop()
			self.camera_workers = None
		self.log.info("done cleanup")

if __name__ == '__main__':
	from typedef.cfg import load_config
	from sys import argv
	
	config_path = './config/local_nn.json' if len(argv) < 2 else argv[1]
	local_cfg = load_config(config_path)

	moenet = MoeNet(config_path, local_cfg)
	try:
		moenet.run()
	finally:
		moenet.cleanup()