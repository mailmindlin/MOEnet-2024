from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Union, List
import logging, os.path
from multiprocessing import Process, get_context
from queue import Empty
from pathlib import Path
from logging import Logger
from typedef import worker
from typedef.cfg import (
	SlamConfig, NNConfig, LocalConfig,
	AprilTagFieldJSON, CameraConfig, OakSelector,
	AprilTagFieldRef, AprilTagFieldConfig, AprilTagInfo, AprilTagList,
)

if TYPE_CHECKING:
	from typedef.common import Pose3dJSON
	from typedef.cfg import Mat44
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
		self.log = log
		self.config = config
		self.config_path = config_path
		self.at_cache: Dict[Union[str, AprilTagFieldJSON], Path] = dict()
		self.nn_cache: Dict[str, worker.ObjectDetectionConfig] = dict()
		self._tempfiles = list()
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

	def _write_apriltags(self, config: SlamConfig) -> Optional[Path]:
		"Write AprilTag info to file, in a format that SpectacularAI can read"
		
		if config.apriltagPath is None:
			return None
		# Redundant spec
		if config.apriltagConfig is not None:
			self.log.warn("AprilTag config was specified along with path (expected exactly one)")
			return None
		from pathlib import Path
		path = Path(config.apriltagPath)
		if not path.exists():
			self.log.error("AprilTag config path does not exist: %s", path)
			return None
	
	def _resolve_selector(self, cid: CameraId, raw_selector: Union[str, OakSelector]) -> OakSelector:
		if isinstance(raw_selector, str):
			for selector in self.config.camera_selectors:
				if selector.id == raw_selector:
					return selector
		else:
			return raw_selector
	
	def _resolve_apriltag(self, cid: CameraId, apriltag: Union[AprilTagFieldRef, AprilTagFieldConfig, None]) -> Optional[Path]:
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
				atRaw = AprilTagFieldJSON.parse_file(apriltagPath)
			except ValueError:
				self.log.exception("Camera %s requested SLAM with AprilTags at %s, but that file is in the wrong format", cid, apriltagPath)
				return None
			else:
				cache_key = str(apriltag.path)
			
			def pose_to_mat44(pose: 'Pose3dJSON') -> 'Mat44':
				quat = pose["rotation"]["quaternion"]
				w = quat["W"]
				x = quat["X"]
				y = quat["Y"]
				z = quat["Z"]
				trans = pose["translation"]

				return [
					[2*(w*w+x*x) - 1, 2*(x*y-w*z),     2*(x*z-w*y),     trans['x']],
					[2*(x*y+w*z),     2*(w*w-y*y) - 1, 2*(y*z-w*x),     trans['y']],
					[2*(x*z-w*y),     2*(y*z+w*x),     2*(w*w-z*z) - 1, trans['z']],
					[0.0, 0.0, 0.0, 1.0],
				]
			
			atData = AprilTagFieldConfig(
				field=atRaw.field,
				tags=AprilTagList(__root__=[
					AprilTagInfo(
						id=tag.ID,
						size=apriltag.tagSize,
						family=apriltag.tagFamily,
						tagToWorld=pose_to_mat44(tag.pose)
					)
					for tag in atRaw.tags
				])
			)
		else:
			apriltag: AprilTagFieldConfig
			# I'm not sure if this is ever cached
			if (cached := self.at_cache.get(apriltag, None)) is not None:
				return cached
			else:
				atData = apriltag
				cache_key = apriltag
		
		from tempfile import NamedTemporaryFile
		apriltagFile = NamedTemporaryFile('w', suffix='.json', encoding='utf8')
		apriltagFile.write(atData.json())
		apriltagFile.flush()
		self._tempfiles.append(apriltagFile)
		result = Path(apriltagFile.name).absolute()
		self.log.info("Create temp file %s", result)
		self.log.info("AprilTag info: %s", atData.json())
		assert result.exists()
		self.at_cache[cache_key] = result
		return result
	
	def _resolve_slam(self, cid: CameraId, raw_slam: Union[bool, SlamConfig]) -> Optional[SlamConfig]:
		if raw_slam == False:
			return None
		elif raw_slam == True:
			raw_slam: Optional[SlamConfig] = self.config.slam
			if raw_slam is None:
				self.log.warn("Camera %s requested global SLAM, but no config exists", cid)
				return None
		
		try:
			apriltagPath = self._resolve_apriltag(cid, raw_slam.apriltag)		
			return worker.SlamConfig(
				backend=raw_slam.backend,
				syncNN=raw_slam.syncNN,
				slam=raw_slam.slam,
				vio=raw_slam.vio,
				apriltagPath=str(apriltagPath),
			)
		except:
			self.log.exception("Error resolving SLAM config for camera %s", cid)
			return None


	def process_one(self, camera: CameraConfig, idx: int = 0) -> worker.InitConfig:
		cid = CameraId(idx, camera.id)
		selector = self._resolve_selector(cid, camera.selector)
		slam_cfg = self._resolve_slam(cid, camera.slam)
		object_detection = self._resolve_pipeline(cid, camera.object_detection)

		return worker.InitConfig(
			id=camera.id,
			selector=selector,
			max_usb=camera.max_usb,
			optional=camera.optional,
			pose=camera.pose,
			slam=slam_cfg,
			object_detection=object_detection,
		)

	def start(self):
		for i, camera in enumerate(self.config.cameras):
			init_cfg = self.process_one(camera, i)
			
			wh = WorkerHandle(f"worker_{i}", init_cfg)
			self._workers.append(wh)
			wh.start()
	
	def stop(self):
		print("Sending stop command to worker")
		for child in self._workers:
			child.cmd_queue.put(worker.CmdChangeState(target=worker.WorkerState.STOPPED), block=True, timeout=1.0)
		for child in self._workers:
			child.stop()
		self._workers.clear()
	
	def __iter__(self):
		return self._workers.__iter__()


class WorkerHandle:
	"Manage a single worker"
	
	proc: Process
	def __init__(self, name: str, config: worker.InitConfig, *, ctx: Optional['BaseContext'] = None) -> None:
		from worker import main as worker_main
		if ctx is None:
			ctx = get_context('spawn')
		
		self.name = name
		self.child_state = None
		self.log = logging.getLogger(name)
		
		self.cmd_queue = ctx.Queue()
		self.data_queue = ctx.Queue()
		self.proc = ctx.Process(
			target=worker_main,
			args=[config, self.data_queue, self.cmd_queue],
			daemon=True,
		)
	
	def start(self):
		self.proc.start()

	def stop(self):
		try:
			self.log.info("Stopping...")
			self.cmd_queue.put(worker.CmdChangeState(target=worker.WorkerState.STOPPED), block=True, timeout=1.0)
			self.proc.join(3.0)
			print("Joined worker")
		except:
			self.proc.kill()
			self.proc.join()
		finally:
			self.proc.close()
		self.log.info("Stopped")
	
	def poll(self):
		while True:
			try:
				packet = self.data_queue.get(block=True, timeout=0.01)
			except Empty:
				break
			else:
				if isinstance(packet, worker.MsgChangeState):
					self.child_state = packet.current
				yield packet