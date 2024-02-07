from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union, Union
import logging, os.path
from multiprocessing import Process, get_context
from queue import Empty
from pathlib import Path
from logging import Logger
from dataclasses import dataclass

from typedef import apriltag
from . import msg as worker
from typedef.pipeline import (
    PipelineConfig, PipelineConfigWorker, PipelineStageWorker,
	ApriltagStageWorker, SlamStageWorker
)
from typedef.common import (
	OakSelector
)
from typedef.cfg import PipelineDefinition, LocalConfig, CameraConfig
from typedef.geom import Pose3d, Transform3d
from wpiutil.log import DataLog, StringLogEntry, IntegerLogEntry

if TYPE_CHECKING:
	from multiprocessing.context import BaseContext
	from queue import Queue


class CameraId:
	"Helper to print out camera IDs"
	def __init__(self, idx: int, name: Optional[str] = None) -> None:
		self.idx = idx
		self.name = name
	
	def __str__(self):
		if self.name is None:
			return f'#{self.idx}'
		else:
			return f'#{self.idx} (name {self.name})'


@dataclass
class ResolvedApriltag:
	wpi: apriltag.WpiInlineAprilTagField
	sai: apriltag.SaiAprilTagFieldRef


class WorkerConfigResolver:
	def __init__(self, log: Logger, config: LocalConfig, config_path: Optional[Path] = None):
		self.log = log.getChild('config')
		self.config = config
		self.config_path = config_path
		self.pipelines: dict[str, PipelineDefinition] = dict()
		self.at_cache: dict[str, ResolvedApriltag] = dict()
		"Cache for AprilTag config resolutions"
		self.nn_cache: dict[str, worker.ObjectDetectionConfig] = dict()
		"Cache object detection resolutions"
		self._tempdir = None

		# Resolve presets
		for pipeline in self.config.pipelines:
			self.pipelines[pipeline.id] = self._resolve_pipeline(None, pipeline.stages)
	
	def _resolve_path(self, relpart: Union[str, Path]) -> Path:
		"Resolve a path relative to the config directory"
		return (Path(self.config_path).parent / os.path.expanduser(relpart)).resolve()
	def _basepath(self):
		return Path(self.config_path).parent
	
	def _resolve_nn(self, cid: CameraId, pipeline_id: Optional[str]) -> Optional[worker.ObjectDetectionConfig]:
		"Resolve a pipeline ID into a config"
		if pipeline_id is None:
			return None
		self.log.debug("Resolving pipeline '%s' for camera %s", pipeline_id, cid)

		# Prefer cached results
		if (cached := self.nn_cache.get(pipeline_id, None)) is not None:
			return cached
		
		# Find definition (linear search is probably fine here)
		try:
			pipeline_def = next(p for p in self.config.detection_pipelines if p.id == pipeline_id)
		except StopIteration:
			# Fail safe, just disable the camera
			self.log.error("Camera %s requested pipeline %s, but it wasn't defined", cid, pipeline_id)
			return None
		
		# Resolve blobPath relative to config file
		blobPath = self._resolve_path(pipeline_def.blobPath)
		self.log.info("Resolved NN blob path '%s' -> '%s'", pipeline_def.blobPath, str(blobPath))
		if not blobPath.exists():
			self.log.error("Camera %s requested pipeline %s with a blob at %s but that file doesn't exist", cid, pipeline_id, blobPath)
			return None
		
		if pipeline_def.config is not None:
			# Inline config
			if pipeline_def.configPath is not None:
				self.log.warning("Camera %s requested pipeline %s with both an internal and external config", cid, pipeline_id)
			nn_cfg = pipeline_def.config
		elif pipeline_def.configPath is not None:
			# Load pipeline from file
			configPath = self._resolve_path(pipeline_def.configPath)
			if not configPath.exists():
				self.log.error("Camera %s requested pipeline %s with a config at %s but that file doesn't exist", cid, pipeline_id, configPath)
				return None
			try:
				nn_cfg = NNConfig.parse_file(configPath)
			except:
				self.log.exception("Camera %s requested pipeline %s with a config at %s but that file doesn't exist", cid, pipeline_id, configPath)
		else:
			self.log.error("Camera %s requested pipeline %s with no config", cid, pipeline_id)
			return None
		
		object_detection = worker.ObjectDetectionConfig(
			confidence_threshold=nn_cfg.confidence_threshold,
			iou_threshold=nn_cfg.iou_threshold,
			labels=nn_cfg.labels,
			depthLowerThreshold=nn_cfg.depthLowerThreshold,
			depthUpperThreshold=nn_cfg.depthUpperThreshold,
			classes=nn_cfg.classes,
			coordinateSize=nn_cfg.coordinateSize,
			anchors=nn_cfg.anchors,
			anchor_masks=nn_cfg.anchor_masks,
			blobPath=str(blobPath)
		)
		self.nn_cache[pipeline_id] = object_detection
		return object_detection
	
	def _resolve_selector(self, cid: CameraId, raw_selector: Union[str, OakSelector]) -> OakSelector:
		"Resolve an OakSelector, possibly by name"
		if isinstance(raw_selector, str):
			for selector in self.config.camera_selectors:
				if selector.id == raw_selector:
					return selector
		else:
			return raw_selector

	def _resolve_pipeline(self, cid: CameraId | None, pipeline: str | PipelineConfig | None) -> PipelineConfigWorker | None:
		if pipeline is None:
			return None
		if isinstance(pipeline, str):
			try:
				return self.pipelines[pipeline]
			except KeyError:
				self.log.warning("Camera %s requested preset pipeline %s, but that preset doesn't exist", cid, pipeline)
				return None
		
		stages: list[PipelineStageWorker] = list()
		for i, stage in enumerate(pipeline.root):
			try:
				if stage.stage == 'inherit':
					stages.extend(self._resolve_pipeline(cid, stage.id))
				elif stage.stage == 'apriltag':
					args = dict(stage)
					args['apriltags'] = stage.apriltags.load(self._basepath()).to_wpi_inline().store(self._basepath())
					stages.append(ApriltagStageWorker(**args))
				elif stage.stage == 'slam':
					args = dict(stage)
					args['apriltags'] = stage.apriltags.load(self._basepath()).to_sai_inline().store(self._basepath())
					stages.append(SlamStageWorker(**args))
				elif stage.stage == 'nn':
					args = dict(stage)
				else:
					stages.append(stage)
			except:
				if stage.optional:
					self.log.warning("Camera %s had error in stage %d", cid, i, exc_info=True)
					continue
				else:
					self.log.exception("Camera %s had error in stage %d", cid, i)
					raise
		return stages
	
	def _resolve_slam(self, cid: CameraId, raw_slam: Union[str, PipelineConfig, None]) -> Optional[PipelineConfig]:
		"Resolve SLAM configuration. We use global SLAM config for when `raw_slam=True`"
		if raw_slam is None:
			return None
		elif isinstance(raw_slam, str):
			# Lookup global
			for preset in self.config.presets:
				if preset.id == raw_slam:
					slam_cfg = preset
					break
			else:
				self.log.warning("Camera %s requested preset %s, but no config exists", cid, raw_slam)
				return None
		else:
			slam_cfg = raw_slam
		slam_cfg: PipelineConfig

		object_detection = self._resolve_nn(cid, slam_cfg.object_detection)
		
		try:
			apriltagPath = self._resolve_apriltag(cid, slam_cfg.apriltag)
			slam_cfg: PipelineConfigBase
			return worker.WorkerPipelineConfig(
				backend=slam_cfg.backend,
				syncNN=slam_cfg.syncNN,
				slam=slam_cfg.slam,
				vio=slam_cfg.vio,
				streams=slam_cfg.streams,
				slam_save=slam_cfg.slam_save,
				slam_load=slam_cfg.slam_load,
				telemetry=slam_cfg.telemetry,
				apriltag_explicit=slam_cfg.apriltag_explicit,
				apriltagPath=str(apriltagPath) if (apriltagPath is not None) else None,
				object_detection=object_detection,
			)
		except:
			self.log.exception("Error resolving SLAM config for camera %s", cid)
			return None
	
	def process_one(self, camera: CameraConfig, idx: int = 0) -> worker.WorkerInitConfig:
		"Resolve the config for a single camera"
		cid = CameraId(idx, camera.id)
		selector = self._resolve_selector(cid, camera.selector)
		pipeline = self._resolve_pipeline(cid, camera.pipeline)

		if pipeline is None:
			pipeline = []

		return worker.WorkerInitConfig(
			id=camera.id or str(cid),
			selector=selector,
			max_usb=camera.max_usb,
			retry=camera.retry,
			robot_to_camera=camera.pose,
			pipeline=pipeline,
		)

	def cleanup(self):
		if self._tempdir is not None:
			self._tempdir.cleanup()
	
	def __iter__(self):
		for i, camera in enumerate(self.config.cameras):
			init_cfg = self.process_one(camera, i)
			yield init_cfg



class WorkerManager:
	def __init__(self, log: Logger, config: LocalConfig, config_path: Optional[Path] = None, datalog: Optional['DataLog'] = None, vidq: Optional['Queue'] = None) -> None:
		self.log = log.getChild('worker')
		self.config = WorkerConfigResolver(self.log, config, config_path)
		self._workers: list['WorkerHandle'] = list()
		self.datalog = datalog
		self.ctx = get_context('spawn')
		self.video_queue = vidq

	def start(self):
		"Start all camera processes"
		for i, cfg in enumerate(self.config):
			name = cfg.id if cfg.id is not None else f'cam_{i}'
			wh = WorkerHandle(name, cfg, log=self.log, datalog=self.datalog, ctx=self.ctx, vidq=self.video_queue)
			self._workers.append(wh)
			wh.start()
	
	def stop(self):
		"Stop camera subprocesses"
		self.log.info("Sending stop command to workers")
		for child in self._workers:
			child.cmd_queue.put(worker.CmdChangeState(target=worker.WorkerState.STOPPED), block=True, timeout=1.0)
		
		self.log.info("Stopping workers")
		for child in self._workers:
			child.close()
		self.log.info("Workers stopped")
		self._workers.clear()

		self.config.cleanup()
	
	def enable_stream(self, worker_name: str, stream: str, enable: bool):
		for worker in self._workers:
			if worker.config.id == worker_name:
				worker.enable_stream(stream, enable)
				return True
		return False
	
	def __iter__(self):
		"Iterate through camera handles"
		return self._workers.__iter__()

class WorkerHandle(Subprocess[worker.WorkerMsg, worker.AnyCmd, worker.AnyMsg]):
	def __init__(self, name: str, config: worker.WorkerInitConfig, *, log: logging.Logger | None = None, ctx: BaseContext | None = None, datalog: Optional['DataLog'] = None, vidq: Optional['Queue'] = None):
		if ctx is None:
			ctx = get_context('spawn')
		
		super().__init__(
			name,
			log=child_logger(name, log),
			cmd_queue=0,
			msg_queue=0,
			daemon=True, ctx=ctx)

		self.datalog = datalog
		if datalog is not None:
			logConfig = StringLogEntry(self.datalog, f'worker/{name}/config')
			logConfig.append(config.model_dump_json())
			logConfig.finish()
			del logConfig

			self.logStatus = IntegerLogEntry(self.datalog, f'worker/{name}/status')
			self.logLog = StringLogEntry(self.datalog, f'worker/{name}/log')

		self.config = config
		self.video_queue = vidq
		self._require_flush_id = 0
		self._last_flush_id = 0
		self._restarts = 0
		self.robot_to_camera = config.robot_to_camera
		self.add_handler(worker.MsgLog, self._handle_log)
		self.add_handler(worker.MsgFlush, self._handle_flush)
		self.add_handler(worker.MsgChangeState, self._handle_changestate)

	def _get_args(self):
		return (
			self.config,
			self.msg_queue,
			self.cmd_queue,
			self.video_queue,
		)
	@property
	def target(self):
		from worker.worker import main as worker_main
		return worker_main
	
	def make_stop_command(self) -> worker.AnyCmd:
		return worker.CmdChangeState(target=worker.WorkerState.STOPPED)
	def enable_stream(self, stream: str, enable: bool):
		self.send(worker.CmdEnableStream(stream=stream, enable=enable))
	
	def flush(self):
		self._require_flush_id += 1
		self.send(worker.CmdFlush(id=self._require_flush_id))
	
	# Message handlers
	def _handle_log(self, packet: worker.MsgLog):
		log = self.log if packet.name == 'root' else self.log.getChild(packet.name)
		log.log(packet.level, packet.msg)
		if self.datalog is not None:
			self.logLog.append(f'[{logging.getLevelName(packet.level)}]{packet.name}:{packet.msg}')
	
	def _handle_flush(self, packet: worker.MsgFlush):
		self.log.debug('Finished flush %d', packet.id)
		self._last_flush_id = max(self._last_flush_id, packet.id)
	
	def _handle_changestate(self, packet: worker.MsgChangeState):
		self.child_state = packet.current
		if self.datalog is not None:
			self.logStatus.append(int(self.child_state))
	
	def handle_default(self, msg: worker.WorkerMsg) -> worker.AnyMsg | None:
		if self._last_flush_id < self._require_flush_id:
			# Packets are invalidated by a flush
			self.log.info("Skipping packet (flushed)")
			return None
		else:
			return msg
	
	def handle_dead(self):
		optional = self.config.retry.optional
		self._restarts += 1
		can_retry = self._restarts < self.config.retry.restart_tries

		if optional:
			self.log.warning('Unexpectedly exited')
			self.child_state = worker.WorkerState.STOPPING
		else:
			self.log.error('Unexpectedly exited')
		# Cleanup process
		self.stop(ask=False)
		if can_retry:
			self.child_state = worker.WorkerState.STOPPED
			self.log.info("Restarting (%d of %d)", self._restarts, self.config.retry.restart_tries - 1)
			# TODO: honor connection_delay?
			self.start()
		elif optional:
			self.child_state = worker.WorkerState.STOPPED
		else:
			self.child_state = worker.WorkerState.FAILED
			raise RuntimeError(f'Camera {self.name} unexpectedly exited')
		
class WorkerHandle0:
	"Manage a single camera worker"
	
	proc: Process
	def __init__(self, name: str, config: worker.WorkerInitConfig, *, log: Optional[logging.Logger] = None, ctx: Optional['BaseContext'] = None, datalog: Optional['DataLog'] = None, vidq: Optional['Queue'] = None):
		if ctx is None:
			ctx = get_context('spawn')
		self._ctx = ctx
		
		self.name = name
		self.child_state = None
		self.log = log.getChild(name) if (log is not None) else logging.getLogger(name)
		self.datalog = datalog
		if datalog is not None:
			logConfig = StringLogEntry(self.datalog, f'worker/{name}/config')
			logConfig.append(config.model_dump_json())
			logConfig.finish()
			del logConfig

			self.logStatus = IntegerLogEntry(self.datalog, f'worker/{name}/status')
			self.logLog = StringLogEntry(self.datalog, f'worker/{name}/log')
		
		self.config = config
		# self.log.info("Start with config %s", config.model_dump_json())
		self.proc = None
		self._restarts = 0
		self.robot_to_camera = config.robot_to_camera
		self.cmd_queue = ctx.Queue()
		self.data_queue = ctx.Queue()
		self.video_queue = vidq
		self._require_flush_id = 0
		self._last_flush_id = 0
	
	def start(self):
		if self.proc is not None:
			self.log.warning('Started twice!')
			return
		
		from worker.worker import main as worker_main
		self.proc = self._ctx.Process(
			target=worker_main,
			args=[self.config, self.data_queue, self.cmd_queue, self.video_queue],
			daemon=True,
			name=f'moenet_{self.name}'
		)
		self.proc.start()

	def stop(self, send_command: bool = True):
		if self.proc is None:
			return
		try:
			# Try stopping nicely
			try:
				self.log.info("Stopping...")
				if send_command:
					self.cmd_queue.put(worker.CmdChangeState(target=worker.WorkerState.STOPPED), block=True, timeout=1.0)
				self.proc.join(1.0)
			except:
				self.log.exception("Error on join")
			
			if self.proc.is_alive():
				self.proc.kill()
			
			try:
				self.proc.join()
			except:
				self.log.exception('Exception on join')
		finally:
			self.log.debug("close")
			self.proc.close()
		self.proc = None
		self.log.info("Stopped")
	
	def enable_stream(self, stream: str, enable: bool):
		self.send(worker.CmdEnableStream(stream=stream, enable=enable))
	
	def send(self, command: Union[worker.CmdChangeState, worker.CmdPoseOverride, worker.CmdFlush, worker.CmdEnableStream]):
		self.cmd_queue.put(command, block=True, timeout=1.0)
	
	def flush(self):
		self._require_flush_id += 1
		self.send(worker.CmdFlush(id=self._require_flush_id))
	
	def _handle_dead(self):
		optional = self.config.retry.optional
		self._restarts += 1
		can_retry = self._restarts < self.config.retry.restart_tries

		if optional:
			self.log.warning('Unexpectedly exited')
			self.child_state = worker.WorkerState.STOPPING
		else:
			self.log.error('Unexpectedly exited')
		# Cleanup process
		self.stop(False)
		if can_retry:
			self.child_state = worker.WorkerState.STOPPED
			self.log.info("Restarting (%d of %d)", self._restarts, self.config.retry.restart_tries - 1)
			# TODO: honor connection_delay?
			self.start()
		elif optional:
			self.child_state = worker.WorkerState.STOPPED
		else:
			self.child_state = worker.WorkerState.FAILED
			raise RuntimeError(f'Camera {self.name} unexpectedly exited')

	def poll(self):
		"Process messages from worker"
		if self.proc is None:
			return
		
		is_alive = True
		while True:
			is_alive = is_alive and self.proc.is_alive()
			try:
				# We want to process any remaining packets even if the process died
				# but we know we don't need to block on the queue then
				packet: worker.AnyMsg = self.data_queue.get(block=is_alive, timeout=0.01)
			except Empty:
				break
			else:
				if isinstance(packet, worker.MsgChangeState):
					self.child_state = packet.current
					if self.datalog is not None:
						self.logStatus.append(int(self.child_state))
				elif isinstance(packet, worker.MsgFlush):
					self.log.debug('Finished flush %d', packet.id)
					self._last_flush_id = max(self._last_flush_id, packet.id)
					continue # We don't need to forward this
				elif isinstance(packet, worker.MsgLog):
					self.log.log(packet.level, packet.msg)
					if self.datalog is not None:
						self.logLog.append(f'[{logging.getLevelName(packet.level)}]{packet.msg}')
					continue

				if self._last_flush_id < self._require_flush_id:
					# Packets are invalidated by a flush
					self.log.info("Skipping packet (flushed)")
					continue

				yield packet
		
		if not is_alive:
			self._handle_dead()
	
	def close(self):
		try:
			self.stop(False)
		finally:
			# Cleanup datalog
			if self.datalog is not None:
				self.logLog.finish()
				del self.logLog
				self.logStatus.finish()
				del self.logStatus
				self.data_queue.close()
				self.cmd_queue.close()
