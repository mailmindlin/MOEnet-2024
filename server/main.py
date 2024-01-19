from typing import TYPE_CHECKING, Optional
import signal
import logging
from typedef.cfg import LocalConfig, RemoteConfig
from typedef.net import Status
if TYPE_CHECKING:
	from worker_srv import WorkerManager
	from wpimath.geometry import Pose3d


class InterruptHandler:
	"Context manager to capture SIGINT"
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

		# Set up NetworkTables
		from comms import Comms
		self.nt = Comms(self, self.config)
		self.status = Status.NOT_READY
		self.sleeping = False
		self.camera_workers: Optional['WorkerManager'] = None

		from estimator import PoseEstimator
		self.pose_estimator = PoseEstimator()

		# Set up timer
		if self.config.timer == "system":
			from clock import IdentityTimeMapper, MonoClock
			self.clock = IdentityTimeMapper(MonoClock())
			self.log.info("Selected system timer")
		else:
			try:
				self.log.info("Connecting to NavX timer")
				from clock.navx import NavXTimeMapper
				self.clock = NavXTimeMapper(self.config.timer)
			except:
				self.log.exception("Unable to construct NavX clock")
				self.status = Status.FATAL
				raise
		
		self.build_cameras()
	
	@property
	def status(self) -> 'Status':
		return self._status

	@status.setter
	def status(self, status: 'Status'):
		if status != getattr(self, '_status', None):
			self.nt.tx_status(status)
		self._status = status
	
	def update_config(self, config: str):
		"Apply remote config options"

		self.log.info("Updating config from remote: %", config)

		try:
			parsed_cfg = RemoteConfig.model_validate_json(config, strict=True)
			next_config = self.initial_config.merge(parsed_cfg)
		except ValidationError:
			self.log.exception("Error when parsing remote config")
			self.status = Status.ERROR
			return
		
		# Check if we have to rebuild the camera processes
		update_cameras = (next_config.cameras != self.config.cameras) or (next_config.slam != self.config.slam)

		self.config = next_config
		if update_cameras:
			self.status = Status.INITIALIZING
		self.reset(update_cameras)
	
	def pose_override(self, pose: 'Pose3d'):
		"Update all the "
		self.log.info('Pose override %s', pose)
		if self.camera_workers is not None:
			from typedef.geom import Pose
			from typedef.worker import CmdPoseOverride
			cmd = CmdPoseOverride(pose=Pose.from_wpi(pose))
			for worker in self.camera_workers:
				worker.send(cmd)
				worker.flush()
	
	def stop_cameras(self):
		if self.camera_workers is not None:
			self.log.info("Stopping cameras")
			self.camera_workers.stop()
			self.camera_workers = None
	
	def build_cameras(self):
		if self.camera_workers is not None:
			return
		
		from worker_srv import WorkerManager
		try:
			self.camera_workers = WorkerManager(self.log, self.config, self.config_path)
			self.camera_workers.start()
			self.status = Status.READY
		except:
			self.log.exception("Error starting cameras")
			self.status = Status.ERROR
			raise
	
	def reset(self, flush_cameras: bool = True):
		if len(self.config.cameras) == 0:
			self.nt.tx_error("No cameras")
			self.status = Status.ERROR
		
		if flush_cameras:
			self.build_cameras()
	
	def poll(self):
		# self.log.debug("Tick start")
		self.nt.update()
		from typedef.worker import MsgPose, MsgDetections

		if self.sleeping:
			if self.status in (Status.READY, Status.INITIALIZING, Status.NOT_READY):
				self.status = Status.SLEEPING
		else:
			if self.status in (Status.SLEEPING, Status.INITIALIZING, Status.NOT_READY):
				self.status = Status.READY

		active = True
		while active:
			active = False
			for i, worker in enumerate(self.camera_workers):
				# self.log.info("Poll worker %d", i)
				for packet in worker.poll():
					# self.log.info("Recv packet %s", repr(packet))
					if isinstance(packet, MsgPose):
						self.pose_estimator.record(worker.robot_to_camera, packet)
					elif isinstance(packet, MsgDetections):
						self.pose_estimator.transform_detections(packet.detections)
						self.nt.tx_detections(packet.detections)
						
					active = True
	
	def run(self):
		from clock import Watchdog
		self.reset(True)

		interrupt = False
		def handle_interrupt(*args):
			self.log.info("Exiting (SIGINT)... %s", args)
			nonlocal interrupt
			interrupt = True

		with InterruptHandler(handle_interrupt):
			while not interrupt:
				with Watchdog(1/100) as w: # Cap at 100Hz
					if self.poll():
						w.skip()
						continue
	
	def cleanup(self):
		self.log.info("Cleanup MoeNet")
		try:
			self.stop_cameras()
		except:
			self.log.exception("Error shutting down")
			self.status = Status.FATAL
		else:
			self.status = Status.NOT_READY
		self.nt.close()
		self.log.info("done cleanup")

if __name__ == '__main__':
	from typedef.cfg import LocalConfig
	from pydantic import ValidationError
	from sys import argv
	
	config_path = './config/local_nn.json' if len(argv) < 2 else argv[1]
	with open(config_path, 'r') as f:
		config_data = f.read()
	try:
		local_cfg = LocalConfig.model_validate_json(config_data)
		del config_data
	except ValidationError:
		print("ERROR: Local config validation failure")
		raise

	moenet = MoeNet(config_path, local_cfg)
	try:
		moenet.run()
	finally:
		moenet.cleanup()
