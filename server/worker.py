from __future__ import annotations
from typing import TYPE_CHECKING
import logging
import time
from traceback import format_exception
from typedef.worker import InitConfig, CmdChangeState, MsgChangeState, WorkerState, MsgPose, MsgDetections
from queue import Empty
import signal

if TYPE_CHECKING:
	from multiprocessing import Queue
	from depthai import Device
	from pipeline import MoeNetPipeline

class CameraWorker:
	def __init__(self, config: InitConfig, data_queue: Queue, command_queue: Queue) -> None:
		self.config = config
		self.data_queue = data_queue
		self.command_queue = command_queue

		self._state = None
		self.state = WorkerState.INITIALIZING

		import sys
		handler = logging.StreamHandler(sys.stdout)
		handler.setLevel(logging.INFO)
		# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
		handler.setFormatter(formatter)
		logging.getLogger().addHandler(handler)
		logging.getLogger().setLevel(logging.INFO)

		self.log = logging.getLogger(config.id)
	
	@property
	def state(self):
		return self._state

	@state.setter
	def state(self, next: WorkerState):
		if next != self._state:
			self.data_queue.put(MsgChangeState(previous=self._state, current=next))
			self._state = next
	
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
	
	def attach_oak(self) -> 'Device':
		import depthai as dai
		sel = self.config.selector
		desc = dai.DeviceDesc()
		use_desc = False
		if sel.mxid is not None:
			desc.mxid = sel.mxid
			use_desc = True
		if sel.name is not None:
			desc.name = sel.name
			use_desc = True
		if sel.platform is not None:
			desc.platform = dai.XLinkPlatform.__members__[sel.platform]
			use_desc = True
		if sel.protocol is not None:
			desc.protocol = dai.XLinkProtocol.__members__[sel.protocol]
			use_desc = True
		if use_desc:
			dev_info = dai.DeviceInfo(desc)
		else:
			dev_info = None
		
		ordinal = None if (sel.ordinal is None) or (sel.ordinal == 1) else sel.ordinal
		max_usb = dai.UsbSpeed.__members__[self.config.max_usb] if (self.config.max_usb is not None) else None
		pipeline = self.pipeline.pipeline

		if ordinal is None:
			if dev_info is None:
				if max_usb is None:
					return dai.Device(pipeline)
				else:
					return dai.Device(pipeline, max_usb)
			else:
				if max_usb is None:
					return dai.Device(pipeline, dev_info)
				else:
					return dai.Device(pipeline, dev_info, max_usb)
		else:
			matches = 0
			for info in dai.Device.getAllAvailableDevices():
				raise NotImplementedError("TODO")
	
	def __enter__(self):
		# Build pipeline
		self.log.info("Creating pipeline...")
		self.pipeline = self.make_pipeline()
		self.pipeline.build()
		self.log.info("Built pipeline")
		try:
			self.state = WorkerState.CONNECTING
			self.log.info("Finding OAK")
			self.device = self.attach_oak()
		except RuntimeError:
			self.log.exception("Unable to find OAK")
			if self.config.optional:
				self.state = WorkerState.STOPPED
				exit(0)
			else:
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
			if isinstance(packet, MsgPose) or (isinstance(packet, MsgDetections) and len(packet.detections)>0):
				self.log.info(" -> Send packet %s", repr(packet))
			self.data_queue.put(packet)
	
	def __exit__(self, *args):
		self.state = WorkerState.STOPPING
		self.log.info("Closing session")
		self.session.close()
		self.log.info("Closing device")
		self.device.close()
		self.log.info("Closed")
		self.state = WorkerState.STOPPED


class InterruptHandler:
	def __init__(self, callback) -> None:
		self._callback = callback
	def __enter__(self):
		self._prev = signal.signal(signal.SIGINT, self._callback)

	def __exit__(self, *args):
		assert signal.signal(signal.SIGINT, self._prev) is self._callback

def main(config: InitConfig, data_queue: Queue, command_queue: Queue):
	# Cap at 100Hz
	min_loop_duration_ns = 1e9 / config.maxRefresh
	signal.signal(signal.SIGINT, signal.SIG_IGN)
	with (CameraWorker(config, data_queue, command_queue) as worker, InterruptHandler(lambda *x: print("Child SIGINT")) as x):
		while True:
			t0 = time.monotonic_ns()
			try:
				try:
					if worker.state == WorkerState.PAUSED:
						command = command_queue.get()
					else:
						command = command_queue.get_nowait()
					
					worker.log.info("Recv command %s", repr(command))
					if isinstance(command, CmdChangeState):
						worker.log.info("Got command: CHANGE STATE -> %s", command.target)
						if worker.state == command.target:
							worker.log.warn("Unable to switch to %s (current state is %s)", command.target, worker.state)
						elif command.target in (WorkerState.STOPPING, WorkerState.STOPPED):
							break
						elif command.target in (WorkerState.RUNNING, WorkerState.PAUSED):
							if worker.state in (WorkerState.RUNNING, WorkerState.PAUSED):
								worker.state = command.target
							else:
								worker.log.warn("Unable to swotch to %s (current state is %s)", command.target, worker.state)
				except Empty:
					pass
				
				if worker.state == WorkerState.RUNNING:
					worker.poll()
			except Exception as e:
				# msg = format_exception(e)
				worker.log.exception("Error in loop")
				break
			t1 = time.monotonic_ns()
			loop_speed = t1 - t0
			if loop_speed < min_loop_duration_ns:
				time.sleep((min_loop_duration_ns - loop_speed) / 1e9)
			elif loop_speed > min_loop_duration_ns * 2:
				worker.log.warn("Loop took %dns", loop_speed)

if __name__ == '__main__':
	# Read config from CLI
	import sys
	if len(sys.argv) < 2:
		print("Error: not enough arguments")
		sys.exit(-1)
	
	config = InitConfig.parse_raw(sys.argv[1])
	main(config)