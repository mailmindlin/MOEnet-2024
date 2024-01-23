from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Union, List, Union, Any
import logging, os.path, time
from multiprocessing import Process, get_context
from queue import Empty
from pathlib import Path
from logging import Logger
from typedef import worker
from typedef.wpilib_compat import AprilTagFieldJSON
from typedef.cfg import (
	SlamConfig, SlamConfigBase, NNConfig, LocalConfig,
	CameraConfig, OakSelector,
	AprilTagFieldFRCRef, AprilTagFieldSAIRef, AprilTagFieldConfig, AprilTagInfo,
	AprilTagList, Mat44, Vec4
)
from typedef.geom import Pose3d, Transform3d

if TYPE_CHECKING:
	from multiprocessing.context import BaseContext

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

class WorkerManager:
	def __init__(self, log: Logger, config: LocalConfig, config_path: Optional[Path] = None) -> None:
		self.log = log.getChild('workers')
		self.config = config
		self.config_path = config_path
		self.at_cache: Dict[Union[str, AprilTagFieldJSON], Path] = dict()
		self.nn_cache: Dict[str, worker.ObjectDetectionConfig] = dict()
		self._tempdir = None
		self._workers: List['WorkerHandle'] = list()
	
	def _resolve_path(self, relpart: Union[str, Path]) -> Path:
		"Resolve a path relative to the config directory"
		return (Path(self.config_path).parent / os.path.expanduser(relpart)).resolve()

	def _resolve_pipeline(self, cid: CameraId, pipeline_id: Optional[str]) -> Optional[worker.ObjectDetectionConfig]:
		"Resolve a pipeline ID into a config"
		if pipeline_id is None:
			return None
		self.log.debug("Resolving pipeline '%s' for camera %s", pipeline_id, cid)

		# Prefer cached results
		if (cached := self.nn_cache.get(pipeline_id, None)) is not None:
			return cached
		
		# Find definition (linear search is probably fine here)
		try:
			pipeline_def = next(p for p in self.config.pipelines if p.id == pipeline_id)
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
				self.log.warn("Camera %s requested pipeline %s with both an internal and external config", cid, pipeline_id)
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
		if isinstance(raw_selector, str):
			for selector in self.config.camera_selectors:
				if selector.id == raw_selector:
					return selector
		else:
			return raw_selector
	
	def _resolve_apriltag(self, cid: CameraId, apriltag: Union[AprilTagFieldFRCRef, AprilTagFieldSAIRef, AprilTagFieldConfig, None]) -> Optional[Path]:
		if apriltag is None:
			self.log.info("Camera %s SLAM has no AprilTags", cid)
			return None

		if getattr(apriltag, 'format', None) == 'frc':
			apriltag: AprilTagFieldRef
			# Load path to AprilTag info
			if (cached := self.at_cache.get(apriltag.path, None)) is not None:
				return cached
			apriltagPath = self._resolve_path(apriltag.path)
			if not apriltagPath.exists():
				self.log.warn("Camera %s requested SLAM with AprilTags at %s, but that file doesn't exist", cid, apriltagPath)
				return None
			
			# Load FRC data
			try:
				with open(apriltagPath, 'r') as f:
					at_text = f.read()
			except:
				self.log.exception("Error reading AprilTag config at %s (requested by camera %s)", apriltagPath, cid)
				return None
			
			try:
				atRaw = AprilTagFieldJSON.model_validate_json(at_text)
			except ValueError:
				self.log.exception("Camera %s requested SLAM with AprilTags at %s, but that file is in the wrong format", cid, apriltagPath)
				return None
			else:
				cache_key = str(apriltag.path)
			
			def pose_to_mat44(pose: Pose3d) -> 'Mat44':
				quat = pose.rotation().getQuaternion()
				w = quat.W()
				x = quat.X()
				y = quat.Y()
				z = quat.Z()
				trans = pose.translation()

				return Mat44([
					Vec4([2*(w*w+x*x) - 1, 2*(x*y-w*z),     2*(x*z-w*y),     trans.x]),
					Vec4([2*(x*y+w*z),     2*(w*w-y*y) - 1, 2*(y*z-w*x),     trans.y]),
					Vec4([2*(x*z-w*y),     2*(y*z+w*x),     2*(w*w-z*z) - 1, trans.z]),
					Vec4([0.0, 0.0, 0.0, 1.0]),
				])
			
			atData = AprilTagFieldConfig(
				field=atRaw.field,
				tags=AprilTagList([
					AprilTagInfo(
						id=tag.ID,
						size=apriltag.tagSize,
						family=apriltag.tagFamily,
						tagToWorld=pose_to_mat44(tag.pose)
					)
					for tag in atRaw.tags
				])
			)
		elif getattr(apriltag, 'format', None) == 'sai':
			apriltag: AprilTagFieldSAIRef
			if (cached := self.at_cache.get(apriltag.path, None)) is not None:
				return cached
			apriltagPath = self._resolve_path(apriltag.path)
			if not apriltagPath.exists():
				self.log.warn("Camera %s requested SLAM with AprilTags at %s, but that file doesn't exist", cid, apriltagPath)
				return None
			# Check that it's correct
			with open(apriltagPath, 'r') as f:
				at_json = f.read()
			AprilTagList.model_validate_json(at_json)
			self.at_cache[apriltag.path] = apriltagPath
			return apriltagPath
		else:
			apriltag: AprilTagFieldConfig
			# I'm not sure if this is ever cached
			if (cached := self.at_cache.get(apriltag, None)) is not None:
				return cached
			else:
				atData: AprilTagFieldConfig = apriltag
				cache_key = apriltag
		
		if self._tempdir is None:
			from tempfile import TemporaryDirectory
			self._tempdir = TemporaryDirectory()

		# Write SAI-formatted AprilTag data to a temp file
		result = Path(self._tempdir.name) / f'apriltag_{int(time.time_ns())}.json'
		self.log.info("Create temp file %s for AprilTag data", result)
		at_json = atData.tags.model_dump_json(indent=4)
		with open(result, 'w') as apriltagFile:
			apriltagFile.write(at_json)
		# with open(Path('.') / f'apriltag_{int(time.time_ns())}.json', 'w') as apriltagFile:
		# 	apriltagFile.write(AprilTagList(atData.tags).model_dump_json())
		self.log.debug("AprilTag info: %s", at_json)

		assert result.exists(), "AprilTag file is missing"

		self.at_cache[cache_key] = result
		return result
	
	def _resolve_slam(self, cid: CameraId, raw_slam: Union[bool, SlamConfig]) -> Optional[SlamConfig]:
		"Resolve SLAM configuration. We use global SLAM config for when `raw_slam=True`"
		if raw_slam == False:
			return None
		elif raw_slam == True:
			slam_cfg: SlamConfig = self.config.slam
			if slam_cfg is None:
				self.log.warn("Camera %s requested global SLAM, but no config exists", cid)
				return None
		else:
			slam_cfg = raw_slam
		slam_cfg: SlamConfig
		
		try:
			apriltagPath = self._resolve_apriltag(cid, slam_cfg.apriltag)
			slam_cfg: SlamConfigBase
			return worker.SlamConfig(
				backend=slam_cfg.backend,
				syncNN=slam_cfg.syncNN,
				slam=slam_cfg.slam,
				vio=slam_cfg.vio,
				apriltagPath=str(apriltagPath),
			)
		except:
			self.log.exception("Error resolving SLAM config for camera %s", cid)
			return None

	def process_one(self, camera: CameraConfig, idx: int = 0) -> worker.InitConfig:
		"Resolve the config for a single camera"
		cid = CameraId(idx, camera.id)
		selector = self._resolve_selector(cid, camera.selector)
		slam_cfg = self._resolve_slam(cid, camera.slam)
		object_detection = self._resolve_pipeline(cid, camera.object_detection)

		return worker.InitConfig(
			id=camera.id,
			selector=selector,
			max_usb=camera.max_usb,
			optional=camera.optional,
			robot_to_camera=camera.pose,
			slam=slam_cfg,
			object_detection=object_detection,
		)

	def start(self):
		"Start all camera processes"
		for i, camera in enumerate(self.config.cameras):
			init_cfg = self.process_one(camera, i)
			
			wh = WorkerHandle(f"worker_{i}", init_cfg, log=self.log)
			self._workers.append(wh)
			wh.start()
	
	def stop(self):
		"Stop camera subprocesses"
		self.log.info("Sending stop command to workers")
		for child in self._workers:
			child.cmd_queue.put(worker.CmdChangeState(target=worker.WorkerState.STOPPED), block=True, timeout=1.0)
		self.log.info("Stopping workers")
		for child in self._workers:
			child.stop(False)
		self.log.info("Workers stopped")
		self._workers.clear()
		if self._tempdir is not None:
			self._tempdir.cleanup()
	
	def __iter__(self):
		"Iterate through camera handles"
		return self._workers.__iter__()


class WorkerHandle:
	"Manage a single camera worker"
	
	proc: Process
	def __init__(self, name: str, config: worker.InitConfig, *, log: Optional[logging.Logger] = None, ctx: Optional['BaseContext'] = None) -> None:
		from worker import main as worker_main
		if ctx is None:
			ctx = get_context('spawn')
		
		self.name = name
		self.child_state = None
		self.log = log.getChild(name) if (log is not None) else logging.getLogger(name)
		
		self.config = config
		print("worker config", config.model_dump_json())
		self._restarts = 0
		self.robot_to_camera = config.robot_to_camera
		self.cmd_queue = ctx.Queue()
		self.data_queue = ctx.Queue()
		self.proc = ctx.Process(
			target=worker_main,
			args=[config, self.data_queue, self.cmd_queue],
			daemon=True,
			name=f'moenet_{name}'
		)
		self._require_flush_id = 0
		self._last_flush_id = 0
	
	def start(self):
		self.proc.start()

	def stop(self, send_command: bool = True):
		if self.proc is None:
			return
		try:
			try:
				self.log.info("Stopping...")
				if send_command:
					self.cmd_queue.put(worker.CmdChangeState(target=worker.WorkerState.STOPPED), block=True, timeout=1.0)
				self.proc.join(3.0)
			except:
				self.log.exception("Error on join")
				self.proc.kill()
				try:
					self.proc.join()
				except:
					self.log.exception('Worker exception on join')
		finally:
			self.proc.close()
		self.proc = None
		self.log.info("Stopped")
	
	def send(self, command: Union[worker.CmdChangeState, worker.CmdPoseOverride, worker.CmdFlush]):
		self.cmd_queue.put(command, block=True, timeout=1.0)
	
	def flush(self):
		self._require_flush_id += 1
		self.send(worker.CmdFlush(id=self._require_flush_id))
	
	def poll(self):
		if self.proc is None:
			return
		
		is_alive = True
		while True:
			is_alive = is_alive and self.proc.is_alive()
			try:
				# We want to process any remaining packets even if the process died
				# but we know we don't need to block on the queue then
				packet: Union[worker.MsgPose, worker.MsgDetections, worker.MsgChangeState] = self.data_queue.get(block=is_alive, timeout=0.01)
			except Empty:
				break
			else:
				if isinstance(packet, worker.MsgChangeState):
					self.child_state = packet.current
				elif isinstance(packet, worker.MsgFlush):
					self.log.debug('Finished flush %d', packet.flush_id)
					self._last_flush_id = max(self._last_flush_id, packet.flush_id)
					continue # We don't need to forward this
				
				if self._last_flush_id < self._require_flush_id:
					# Packets are invalidated by a flush
					continue

				yield packet
		
		if not is_alive:
			if not self.config.optional:
				self.log.error('Camera process unexpectedly exited')
			else:
				self.log.warn('Camera process unexpectedly exited')
			# Cleanup process
			self.child_state = worker.WorkerState.FAILED
			self.stop(False)

			if (not self.config.optional):
				raise RuntimeError('Camera unexpectedly exited')
			
			#TODO: restart-retry logic