"Helper to resolve camera configs"

from __future__ import annotations
from typing import Optional
from pydantic import ValidationError
from pathlib import Path
from logging import Logger
from dataclasses import dataclass

from . import msg as worker
from typedef import apriltag
from typedef.pipeline import (
	PipelineConfig, PipelineConfigWorker, PipelineStage, PipelineStageWorker,
	AprilTagStageConfig, WorkerAprilTagStageConfig,
	SlamStageConfig, WorkerSlamStageConfig,
	ObjectDetectionStageConfig, NNConfig
)
from typedef.common import OakSelector
from typedef.cfg import PipelineDefinition, LocalConfig, CameraConfig, CameraSelectorDefinition
from util.path import resolve_path

@dataclass
class PipelinePresetId:
	id: str
	
	def __str__(self):
		return f"Pipeline preset '{self.id}'"


class CameraId:
	"Helper to print out camera IDs"
	def __init__(self, idx: int, name: Optional[str] = None) -> None:
		self.idx = idx
		self.name = name
	
	def __str__(self):
		if self.name is None:
			return f"camera_{self.idx}"
		else:
			return f"Camera '{self.name}')"


class WorkerConfigResolver:
	"""
	Helper to resolve the configuration of each worker.
	Our config JSON format isn't the easiest to process (e.g., references), so this simplifies it
	"""
	def __init__(self, log: Logger, config: LocalConfig, config_path: Optional[Path] = None):
		self.log = log.getChild('config')
		self.config = config
		self.config_path = config_path
		self._tempdir = None
		self.pipelines: dict[str, PipelineDefinition] = dict()
		"Pipeline presets"

		# Resolve presets
		for pipeline in self.config.pipelines:
			self.pipelines[pipeline.id] = self._resolve_pipeline(PipelinePresetId(pipeline.id), pipeline.stages)

	@property
	def _base_path(self):
		"Base to resolve relative paths in the config relative to"
		return Path(self.config_path).parent
	
	def _resolve_path(self, relpart: str | Path) -> Path:
		"Resolve a path relative to the config directory"
		return resolve_path(self._base_path, relpart)
	
	def _make_tempdir(self) -> Path:
		"Make the tempdir (if it doesn't exist)"
		if self._tempdir is None:
			import tempfile
			self._tempdir = tempfile.TemporaryDirectory(
				prefix='moenet',
			)
		return Path(self._tempdir.name)
	
	def _resolve_stage_slam(self, src: SlamStageConfig) -> WorkerSlamStageConfig:
		"Resolve 'slam' pipeline stage"
		# Convert to SAI format
		apriltags = src.apriltags
		if apriltags is not None:
			apriltags = apriltags.convert(apriltag.AprilTagFieldRefSai, self._base_path, self._make_tempdir)
		map_save = src.map_save
		if map_save is not None:
			map_save = self._resolve_path(map_save)
		map_load = src.map_load
		if map_load is not None:
			map_load = self._resolve_path(map_load)
		return WorkerSlamStageConfig(**dict(
			src,
			apriltags=apriltags,
			map_save=map_save,
			map_load=map_load,
		))
	
	def _resolve_stage_apriltag(self, src: AprilTagStageConfig) -> WorkerAprilTagStageConfig:
		"Resolve 'apriltag' pipeline stage"
		try:
			apriltags = src.apriltags.convert(apriltag.AprilTagFieldInlineWpi, self._base_path, self._make_tempdir)
		except:
			raise

		return WorkerAprilTagStageConfig(
			**src.model_dump(exclude={'apriltags'}),
			apriltags=apriltags,
		)

	def _resolve_stage_nn(self, cid: CameraId, nn_stage: ObjectDetectionStageConfig) -> ObjectDetectionStageConfig:
		"Resolve a 'nn' pipeline stage"

		self.log.debug("%s resolving nn", cid)

		# Resolve blobPath relative to config file
		blobPath = self._resolve_path(nn_stage.blobPath)
		self.log.info("Resolved NN blob path '%s' -> '%s'", nn_stage.blobPath, str(blobPath))
		if not blobPath.exists():
			raise FileNotFoundError(f"blob at '{blobPath}'")
		
		if isinstance(nn_stage.config, (str, Path)):
			# Load pipeline from file
			configPath = self._resolve_path(nn_stage.config)
			try:
				with open(configPath, 'r') as f:
					configRaw = f.read()
				config = NNConfig.model_validate_json(configRaw)
			except FileNotFoundError:
				raise FileNotFoundError(f"config at '{configPath}'")
			except ValidationError as e:
				raise
			except:
				raise RuntimeError(f"Unable to read config at '{configPath}'")
		else:
			# Inline config
			config = nn_stage.config
		
		return ObjectDetectionStageConfig(
			**nn_stage.model_dump(exclude={'config', 'blobPath'}),
			config=config,
			blobPath=blobPath,
		)
	
	def _resolve_stage(self, cid: CameraId | PipelinePresetId, idx: int, stage: PipelineStage) -> list[PipelineStageWorker]:
		# Skip disabled stages
		if not stage.enabled:
			return []
		try:
			match stage.stage:
				# We need to map some stages
				case 'inherit':
					if (parent := self._resolve_pipeline(cid, stage.id)) is not None:
						return parent
					else:
						e = RuntimeError(f"Unable to inherit from pipeline '{stage.id}', as id doesn't exist")
						if self.config.pipelines:
							for pipeline in self.config.pipelines:
								e.add_note(f"Valid pipeline: {pipeline.id}")
						else:
							e.add_note("There are no registered pipelines")
						raise e
				case 'apriltag':
					return [self._resolve_stage_apriltag(stage)]
				case 'slam':
					return [self._resolve_stage_slam(stage)]
				case 'nn':
					return [self._resolve_stage_nn(cid, stage)]
				case _:
					# Passthrough
					return [stage]
		except Exception as e:
			if stage.optional:
				self.log.warning("%s had error in stage #%d (%s)", cid, idx, stage.stage, exc_info=True)
				return []
			else:
				self.log.exception("%s had error in stage #%d (%s)", cid, idx, stage.stage)
				raise

	def _resolve_pipeline(self, cid: CameraId | PipelinePresetId, pipeline: str | PipelineConfig | None) -> PipelineConfigWorker | None:
		"Resolve worker pipeline"
		if pipeline is None:
			return None
		
		if isinstance(pipeline, str):
			self.log.debug("Looking up pipeline %s", pipeline)
			self.log.debug("Pipelines: %s", self.pipelines)
			try:
				res = self.pipelines[pipeline]
				self.log.debug('Resolved pipeline %s: %s', pipeline, res)
				return res
			except KeyError:
				self.log.warning("%s requested preset pipeline %s, but that preset doesn't exist", cid, pipeline)
				return None
		
		stages: list[PipelineStageWorker] = list()
		for i, stage in enumerate(pipeline.root):
			stages.extend(self._resolve_stage(cid, i, stage))
		
		return PipelineConfigWorker(stages)
	
	def _resolve_selector(self, cid: CameraId, raw_selector: str | OakSelector) -> tuple[OakSelector, Optional[CameraSelectorDefinition]]:
		"Resolve an OakSelector, possibly by name"
		if isinstance(raw_selector, str):
			for selector in self.config.camera_selectors:
				if selector.id == raw_selector:
					return (
						OakSelector.model_validate(selector, strict=False, from_attributes=True),
						selector
					)
			else:
				raise KeyError("%s requested named selector '%s', but that was never defined", cid, raw_selector)
		else:
			return (raw_selector, None)
	
	def process_one(self, camera: CameraConfig, idx: int = 0) -> worker.WorkerInitConfig:
		"Resolve the config for a single camera"
		cid = CameraId(idx, camera.name)
		selector, dfn = self._resolve_selector(cid, camera.selector)
		pipeline = self._resolve_pipeline(cid, camera.pipeline)

		if pipeline is None:
			pipeline = []
		
		name = camera.name
		robot_to_camera = camera.pose
		dynamic_pose = camera.dynamic_pose
		if dfn is not None:
			if name is None:
				name = dfn.name
			if robot_to_camera is None:
				robot_to_camera = dfn.pose
			if dynamic_pose is None:
				dynamic_pose = dfn.dynamic_pose
		
		# We need name to exist for logging
		if name is None:
			name = str(cid)
		
		return worker.WorkerInitConfig(
			name=name,
			selector=selector,
			max_usb=camera.max_usb,
			retry=camera.retry,
			robot_to_camera=robot_to_camera,
			dynamic_pose=dynamic_pose,
			pipeline=pipeline,
		)

	def cleanup(self):
		"Clean up temporary files"
		if self._tempdir is not None:
			self._tempdir.cleanup()
			self._tempdir = None
	
	def __iter__(self):
		for i, camera in enumerate(self.config.cameras):
			init_cfg = self.process_one(camera, i)
			yield init_cfg