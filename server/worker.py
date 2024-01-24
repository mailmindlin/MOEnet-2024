from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import logging
from functools import cached_property
from queue import Empty, Full
from typedef.worker import (
	WorkerInitConfig, OakSelector,
	CmdChangeState, MsgChangeState, WorkerState,
	CmdPoseOverride, MsgPose, MsgDetections,
	CmdFlush, MsgFlush,
	MsgLog,
	AnyMsg, AnyCmd
)

if TYPE_CHECKING:
	from multiprocessing import Queue
	import depthai as dai
	from pipeline import MoeNetPipeline


class WorkerStop(Exception):
	pass

class OakNotFoundException(RuntimeError):
	pass


class ForwardHandler(logging.Handler):
	def __init__(self, queue: Queue[AnyMsg], level: logging._Level = 0) -> None:
		super().__init__(level)
		self._queue = queue
	
	def emit(self, record: logging.LogRecord):
		try:
			msg = self.format(record)
			try:
				self._queue.put(MsgLog(level=int(record.levelno), msg=str(msg)), timeout=0.1)
			except Full:
				print("[overflow]", msg)
		except RecursionError:  # See issue 36272
			raise
		except Exception:
			self.handleError(record)


class DeviceManager:
	@staticmethod
	def selector_to_descriptor(selector: OakSelector) -> Optional['dai.DeviceDesc']:
		from depthai import DeviceDesc
		desc = DeviceDesc()
		use_desc = False
		if selector.mxid is not None:
			desc.mxid = selector.mxid
			use_desc = True
		if selector.name is not None:
			desc.name = selector.name
			use_desc = True
		if (platform := selector.platform_dai) is not None:
			desc.platform = platform
			use_desc = True
		if (protocol := selector.protocol_dai) is not None:
			desc.protocol = protocol
			use_desc = True
		
		if use_desc:
			return dai.DeviceInfo(desc)
		else:
			return None
	
	def __init__(self, config: WorkerInitConfig, log: logging.Logger) -> None:
		self.config = config
		self.log = log
		self._retries = 0
		self._last_device_info = None
	
	def _info_matches(self, info: 'dai.DeviceInfo'):
		sel = self.config.selector
		if (mxid := sel.mxid) is not None:
			if info.mxid != mxid:
				return False
		if (name := sel.name) is not None:
			if info.name != name:
				return False
		if (platform := sel.platform_dai) is not None:
			if info.platform != platform:
				return False
		if (protocol := sel.protocol_dai) is not None:
			if info.protocol != protocol:
				return False
		return True
	
	@cached_property
	def max_usb_dai(self) -> Optional['dai.UsbSpeed']:
		max_usb = self.config.max_usb
		from depthai import UsbSpeed
		if (max_usb is None) or (max_usb == 'UNKNOWN'):
			return None
		return UsbSpeed.__members__[max_usb]
	
	def attach_oak(self, pipeline: 'dai.Pipeline', dev_info: Optional['dai.DeviceInfo']):
		from depthai import Device
		device = None
		try:
			try:
				if dev_info is None:
					if (max_usb := self.max_usb_dai) is not None:
						self.log.info('Find device with max_usb=%s', max_usb)
						device = Device(pipeline, max_usb)
					else:
						self.log.info('Find first device')
						device = Device(pipeline)
				else:
					if (max_usb := self.max_usb_dai) is not None:
						self.log.info('Find device with mxid=%s, name=%s, platform=%s, protocol=%s, max_usb=%s', dev_info.mxid, dev_info.name, dev_info.platform, dev_info.protocol, max_usb)
						device = Device(pipeline, dev_info, max_usb)
					else:
						self.log.info('Find device with mxid=%s, name=%s, platform=%s, protocol=%s', dev_info.mxid, dev_info.name, dev_info.platform, dev_info.protocol)
						device = Device(pipeline, dev_info)
			except RuntimeError as e:
				raise OakNotFoundException(*e.args) from e
			# Store last info, for sticky connecting
			self._last_device_info = device.getDeviceInfo()
		except:
			# Better cleanup
			if device is not None:
				device.close()
			raise
		return device
	
	def find_oak(self, pipeline: 'dai.Pipeline') -> 'dai.Device':
		"Find and acquire to OAK camera"
		from depthai import Device
		sel = self.config.selector
		
		ordinal = sel.ordinal

		prev_excs = list()
		while True:
			# Try to connect
			try:
				# Pick best constructor
				if (ordinal is None) or (ordinal == 1):
					dev_info = DeviceManager.selector_to_descriptor(self.config.selector)
					return self.attach_oak(pipeline, dev_info)
				else:
					matches = 0
					for dev_info in Device.getAllAvailableDevices():
						if self._info_matches(dev_info):
							matches += 1
							if matches == ordinal:
								return self.attach_oak(pipeline, dev_info)
					raise OakNotFoundException()
			except RuntimeError as e:
				self._retries += 1
				# We're out of connection tries
				if self._retries > self.config.retry.connection_tries:
					e1 = OakNotFoundException()
					for prev_exc in prev_excs:
						e1.add_note(f'Previous exception: {prev_exc}')
					raise e1 from e
				
				prev_excs.append(e)


class CameraWorker:
	def __init__(self, config: WorkerInitConfig, data_queue: Queue[AnyMsg], command_queue: Queue[AnyCmd]) -> None:
		self.config = config
		self.data_queue = data_queue
		self.command_queue = command_queue

		self._state = None
		self.state = WorkerState.INITIALIZING

		handler = ForwardHandler(data_queue, logging.INFO)
		handler.setFormatter(logging.Formatter('%(name)s:%(message)s'))
		logging.getLogger().addHandler(handler)
		logging.getLogger().setLevel(logging.INFO)

		self.log = logging.getLogger(config.id)

		self.dev_mgr = DeviceManager(config, self.log)
	
	@property
	def state(self):
		return self._state

	@state.setter
	def state(self, next: WorkerState):
		if next != self._state:
			self.data_queue.put(MsgChangeState(previous=self._state, current=next))
			self._state = next
	
	@property
	def is_paused(self):
		return self.state == WorkerState.PAUSED
	
	def make_pipeline(self) -> 'MoeNetPipeline':
		from pipeline import MoeNetPipeline, PipelineConfig
		syncNN = False
		outputRGB = False
		vio = False
		slam = False
		apriltagPath = None
		if self.config.slam is not None:
			slam_cfg = self.config.slam
			syncNN = slam_cfg.syncNN
			outputRGB = slam_cfg.debugImage
			vio = slam_cfg.vio
			slam = slam_cfg.slam
			apriltagPath = slam_cfg.apriltagPath
		
		return MoeNetPipeline(
			PipelineConfig(
				syncNN=syncNN,
				outputRGB=outputRGB,
				vio=vio,
				slam=slam,
				apriltag_path=apriltagPath,
				nn=self.config.object_detection,
			)
		)
	
	def __enter__(self):
		# Build pipeline
		self.log.info("Creating pipeline...")
		self.pipeline = self.make_pipeline()
		self.pipeline.build()
		self.log.info("Built pipeline")
		try:
			self.state = WorkerState.CONNECTING
			self.log.info("Finding OAK")
			self.device = self.dev_mgr.find_oak(self.pipeline.pipeline)
		except OakNotFoundException:
			if self.config.retry.optional:
				self.log.exception("Unable to find OAK")
				self.state = WorkerState.STOPPED
				exit(0)
			else:
				self.log.error("Unable to find OAK")
				self.state = WorkerState.FAILED
				raise
		else:
			mxid = self.device.getMxId()
			self.log.info("Attached to OAK (mxid=%s)", mxid)
		
		from pipeline import MoeNetSession
		self.session = MoeNetSession(self.device, self.pipeline)
		self.state = WorkerState.RUNNING

		return self

	def poll(self):
		self.log.debug("Poll camera")
		for packet in self.session.poll():
			if isinstance(packet, MsgPose):
				self.log.info(" -> Pose %05.03f %05.03f %05.05f %05.05f", packet.pose.translation().x, packet.pose.translation().y, packet.pose.translation().z, packet.poseCovariance[0,0])
			elif isinstance(packet, MsgDetections):
				if len(packet.detections) > 0:
					self.log.info(" -> Send packet %s", repr(packet))
			self.data_queue.put(packet)
	
	def process_command(self, command: AnyCmd):
		"Process a command"

		if isinstance(command, CmdChangeState):
			self.log.info("Got command: CHANGE STATE -> %s", command.target)
			if self.state == command.target:
				self.log.warning("Unable to switch to %s (current state is %s)", command.target, self.state)
			if command.target in (WorkerState.STOPPING, WorkerState.STOPPED):
				# Exit
				self.state = WorkerState.STOPPING
				raise WorkerStop()
			elif command.target in (WorkerState.RUNNING, WorkerState.PAUSED):
				if self.state in (WorkerState.RUNNING, WorkerState.PAUSED):
					self.state = command.target
				else:
					self.log.warning("Unable to switch to %s (current state is %s)", command.target, self.state)
		elif isinstance(command, CmdPoseOverride):
			self.log.info("Got command: OVERRIDE POSE")
			self.session.override_pose(command.pose)
		elif isinstance(command, CmdFlush):
			self.log.info("Got command: FLUSH")
			self.flush()
			# ACK flush
			self.data_queue.put(MsgFlush(id=command.id))
		else:
			self.log.warning("Unknown command: %s", repr(command))
	
	def flush(self):
		"Flush all data from device"
		self.session.flush()
	
	def __exit__(self, *args):
		self.state = WorkerState.STOPPING
		self.log.info("Closing session")
		self.session.close()
		self.log.info("Closing device")
		self.device.close()
		self.log.info("Closed")
		self.state = WorkerState.STOPPED


def main(config: WorkerInitConfig, data_queue: Queue[AnyMsg], command_queue: Queue[AnyCmd]):
	# Cap at 100Hz
	min_loop_duration = 1 / config.maxRefresh
	from util.interrupt import InterruptHandler
	from clock.watchdog import Watchdog
	import signal

	signal.signal(signal.SIGINT, signal.SIG_IGN)
	def handle_sigint(*args):
		print("Child SIGINT")
	
	with (CameraWorker(config, data_queue, command_queue) as worker, InterruptHandler(handle_sigint)):
		while True:
			with Watchdog('worker', min=min_loop_duration, max=0.5, log=worker.log) as w:
				try:
					try:
						if worker.is_paused:
							# We're paused, so we might as well block
							command = command_queue.get()
							w.ignore_exceeded = True
						else:
							command = command_queue.get_nowait()
					except Empty:
						pass
					else:
						worker.process_command(command)
					
					if worker.state == WorkerState.RUNNING:
						worker.poll()
				except WorkerStop:
					worker.log.info("Stopping gracefully")
					break
				except:
					# msg = format_exception(e)
					worker.log.exception("Error in loop")
					worker.state = WorkerState.FAILED
					raise


if __name__ == '__main__':
	# Read config from CLI
	import sys
	if len(sys.argv) < 2:
		print("Error: not enough arguments")
		sys.exit(-1)
	
	with open(sys.argv[1], 'r') as f:
		config_str = f.read()
	config = WorkerInitConfig.model_validate_json(config_str)

	import time
	class FakeQueue:
		def get(self):
			raise Empty()
		get_nowait = get
		def put(self, data):
			time.sleep(0.01)
	try:
		main(config, FakeQueue(), FakeQueue())
	finally:
		print("Bye")