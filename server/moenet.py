from typing import Optional
import logging, sys
from pathlib import Path

from pydantic_core import ValidationError

from typedef.cfg import LocalConfig, RemoteConfig
from typedef.net import Status
from typedef.geom import Pose3d
from worker import msg as wmsg

from comms import Comms
from web.web_srv import RemoteWebServer
from worker.controller import WorkerManager
from estimator import DataFusion
from util.watchdog import Watchdog
from util.interrupt import InterruptHandler
from util.clock import WallClock
from util.timemap import IdentityTimeMapper

class MoeNet:
	camera_workers: Optional[WorkerManager]
	def __init__(self, config_path: str, config: LocalConfig):
		if config.log is not None:
			from util.log import ColorFormatter
			level = config.log.level.upper()
			root = logging.getLogger()
			root.setLevel(level)
			sh = logging.StreamHandler(sys.stdout)
			# sh.setFormatter(logging.Formatter('[%(levelname)s]%(name)s:%(message)s'))
			sh.setFormatter(ColorFormatter())
			root.addHandler(sh)

		self.log = logging.getLogger()
		self.datalog = None
		self.config_path = config_path
		self.config = config
		self.initial_config = config
		self.log.info('Using config from %s', config_path)
		
		# Set up DataLog
		datalog_folder = None
		if self.config.datalog.enabled:
			datalog_folder = Path(config_path).parent.resolve() / (self.config.datalog.folder or 'log')
			if not datalog_folder.exists():
				datalog_folder = None
		
		if datalog_folder is not None:
			from wpiutil.log import DataLog, IntegerLogEntry, StringLogEntry
			from wpi_compat.datalog.log import PyToNtHandler
			
			self.log.info("DataLog write to folder %s", datalog_folder)
			self.datalog = DataLog(dir=str(datalog_folder))
			self.logStatus = IntegerLogEntry(self.datalog, 'meta/status')
			self.logConfig = StringLogEntry(self.datalog, 'meta/config')
			self.logConfig.append(self.config.model_dump_json())
			
			# Write logs to datalog
			# root.addHandler(PyToNtHandler(self.datalog, 'log'))
		else:
			self.datalog = None

		# Set up NetworkTables
		self.nt = Comms(self, self.config)
		self.status = Status.NOT_READY
		self.sleeping = False
		self.camera_workers = None

		self.web = RemoteWebServer(self)

		self.clock = WallClock()

		# Set up timer
		if self.config.timer == "system":
			self.log.info("Selected system timer")
			self.loc_to_net = IdentityTimeMapper(self.clock)
			"Map local time to Rio time"
		else:
			try:
				self.log.info("Connecting to NavX timer")
				from util.navx import NavXTimeMapper
				self.loc_to_net = NavXTimeMapper(self.clock, self.config.timer)
			except:
				self.log.exception("Unable to construct NavX clock")
				self.status = Status.FATAL
				raise

		# Set up PoseEstimator
		self.estimator = DataFusion(
			self.config.estimator,
			log=self.log,
			datalog=self.datalog,
			clock=self.clock,
		)
		
		self.build_cameras()
	
	@property
	def status(self) -> 'Status':
		return self._status

	@status.setter
	def status(self, status: 'Status'):
		if status != getattr(self, '_status', None):
			self.nt.tx_status(status)
			if self.datalog is not None:
				self.logStatus.append(int(status))
		
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
		if self.datalog is not None:
			self.logConfig.append(self.config.model_dump_json())
		
		if update_cameras:
			self.status = Status.INITIALIZING
		self.reset(update_cameras)
	
	def pose_override(self, pose: 'Pose3d'):
		"Update all the "
		self.log.info('Pose override %s', pose)
		if self.camera_workers is not None:
			cmd = wmsg.CmdPoseOverride(pose=pose)
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
		
		try:
			self.camera_workers = WorkerManager(
				self.log,
				self.config,
				config_path=self.config_path,
				datalog=self.datalog,
				vidq=self.web.vidq
			)
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
		self.web.poll()

		if self.sleeping:
			# Transition to sleeping
			if self.status in (Status.READY, Status.INITIALIZING, Status.NOT_READY, Status.ERROR):
				for worker in self.camera_workers:
					worker.send(wmsg.CmdChangeState(target=wmsg.WorkerState.PAUSED))
				self.status = Status.SLEEPING
		else:
			if self.status in (Status.SLEEPING, Status.INITIALIZING, Status.NOT_READY):
				self.status = Status.READY

		# Process packets from cameras
		active = True
		while active:
			active = False
			for worker in self.camera_workers:
				for packet in worker.poll():
					if isinstance(packet, wmsg.MsgPose):
						self.estimator.record_f2r(worker.robot_to_camera, packet)
					elif isinstance(packet, wmsg.MsgDetections):
						self.estimator.record_detections(worker.robot_to_camera, packet)
					active = True
		
		# Write transforms to NT
		if f2r := self.estimator.field_to_robot(fresh=True):
			self.log.debug("Update pose")
			self.nt.tx_pose(f2r)
		if o2r := self.estimator.odom_to_robot(fresh=True):
			self.log.debug("Update correction")
			self.nt.tx_correction(o2r)
		
		# Write detections to NT
		if dets := self.estimator.get_detections(self.loc_to_net, fresh=True):
			self.nt.tx_detections(dets)
	
	def run(self):
		self.reset(True)

		interrupt = False
		def handle_interrupt(*args):
			self.log.warning("Exiting (SIGINT)... %s", args)
			nonlocal interrupt
			interrupt = True

		with InterruptHandler(handle_interrupt):
			while not interrupt:
				with Watchdog('main', min=1/100, max=1/10, log=self.log) as w: # Cap at 100Hz
					if self.poll():
						w.skip()
						continue
		self.log.info(f"Done running int={interrupt}")
	
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
		if self.datalog is not None:
			self.datalog.flush()
			self.datalog.stop()