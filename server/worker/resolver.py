"Helper to resolve camera configs"

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union, cast
import os.path
from pathlib import Path
from logging import Logger
from dataclasses import dataclass

from . import msg as worker
from typedef import apriltag
from typedef.pipeline import (
	PipelineConfig, PipelineConfigWorker, PipelineStageWorker,
	ApriltagStage, ApriltagStageWorker,
	SlamStage, SlamStageWorker,
	ObjectDetectionStage, NNConfig
)
from typedef.common import OakSelector
from typedef.cfg import PipelineDefinition, LocalConfig, CameraConfig
from typedef.geom import Transform3d

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
			return f"Camera #{self.idx}"
		else:
			return f"Camera '{self.name}')"


@dataclass
class ResolvedApriltag:
	wpi: apriltag.AprilTagFieldInlineWpi
	sai: apriltag.AprilTagFieldRefSai


class WorkerConfigResolver:
	def __init__(self, log: Logger, config: LocalConfig, config_path: Optional[Path] = None):
		self.log = log.getChild('config')
		self.config = config
		self.config_path = config_path
		self.at_cache: dict[str, ResolvedApriltag] = dict()
		"Cache for AprilTag config resolutions"
		self._tempdir = None

		self.pipelines: dict[str, PipelineDefinition] = dict()
		# Resolve presets
		for pipeline in self.config.pipelines:
			self.pipelines[pipeline.id] = self._resolve_pipeline(PipelinePresetId(pipeline.id), pipeline.stages)
	
	def _resolve_path(self, relpart: str | Path) -> Path:
		"Resolve a path relative to the config directory"
		return (self._basepath() / os.path.expanduser(relpart)).resolve()

	def _basepath(self):
		return Path(self.config_path).parent
	
	def make_tempdir(self) -> Path:
		"Make the tempdir (if it doesn't exist)"
		if self._tempdir is None:
			import tempfile
			self._tempdir = tempfile.TemporaryDirectory(
				prefix='moenet',
			)
		return Path(self._tempdir.name)
	
	def _resolve_slam(self, src: SlamStage) -> SlamStageWorker:
		apriltags = src.apriltags.convert(apriltag.AprilTagFieldRefSai, self._basepath(), self.make_tempdir)
		return SlamStageWorker(**dict(
			src,
			apriltags=apriltags,
		))
	
	def _resolve_apriltag(self, src: ApriltagStage) -> ApriltagStageWorker:
		return ApriltagStageWorker(**dict(
			src,
			apriltags=src.apriltags.convert(apriltag.AprilTagFieldInlineWpi, self._basepath(), self.make_tempdir),
		))

	def _resolve_nn(self, cid: CameraId, nn_stage: ObjectDetectionStage) -> Optional[ObjectDetectionStage]:
		"Resolve a nn stage"
		self.log.debug("%s resolving nn", cid)

		# Resolve blobPath relative to config file
		blobPath = self._resolve_path(nn_stage.blobPath)
		self.log.info("Resolved NN blob path '%s' -> '%s'", nn_stage.blobPath, str(blobPath))
		if not blobPath.exists():
			self.log.error("%s requested object detection stage with a blob at '%s', but that file doesn't exist", cid, blobPath)
			return None
		
		if isinstance(nn_stage.config, (str, Path)):
			# Load pipeline from file
			configPath = self._resolve_path(nn_stage.config)
			if not configPath.exists():
				self.log.error("%s requested object detection stage with a config at '%s', but that file doesn't exist", cid, configPath)
				return None
			try:
				with open(configPath, 'r') as f:
					configRaw = f.read()
				config = NNConfig.model_validate_json(configRaw)
			except:
				self.log.exception("%s requested object detection stage with a config at %s but that file doesn't exist", cid, configPath)
		else:
			# Inline config
			config = nn_stage.config
		
		return ObjectDetectionStage(
			**dict(
				nn_stage,
				config=config,
				blobPath=blobPath,
			),
		)
	
	def _resolve_selector(self, cid: CameraId, raw_selector: str | OakSelector) -> tuple[OakSelector, Optional[Transform3d]]:
		"Resolve an OakSelector, possibly by name"
		if isinstance(raw_selector, str):
			for selector in self.config.camera_selectors:
				if selector.id == raw_selector:
					return (selector, selector.pose)
			else:
				raise KeyError("%s requested named selector '%s', but that was never defined", cid, raw_selector)
		else:
			return (raw_selector, None)

	def _resolve_pipeline(self, cid: CameraId | PipelinePresetId, pipeline: str | PipelineConfig | None) -> PipelineConfigWorker | None:
		"Resolve worker pipeline"

		if pipeline is None:
			return None
		
		if isinstance(pipeline, str):
			self.log.info("Looking up pipeline %s", pipeline)
			self.log.info("Pipelines: %s", self.pipelines)
			try:
				res = self.pipelines[pipeline]
				self.log.info('Resolved pipeline %s: %s', pipeline, res)
				return res
			except KeyError:
				self.log.warning("%s requested preset pipeline %s, but that preset doesn't exist", cid, pipeline)
				return None
		
		stages: list[PipelineStageWorker] = list()
		for i, stage in enumerate(pipeline.root):
			try:
				match stage.stage:
					# We need to map some stages
					case 'inherit':
						if (parent := self._resolve_pipeline(cid, stage.id)) is not None:
							stages.extend(parent)
						else:
							e = RuntimeError(f"Unable to inherit from pipeline '{stage.id}', as id doesn't exist")
							if self.config.pipelines:
								for pipeline in self.config.pipelines:
									e.add_note(f"Valid pipeline: {pipeline.id}")
							else:
								e.add_note("There are no registered pipelines")
							raise e
					case 'apriltag':
						stages.append(self._resolve_apriltag(stage))
					case 'slam':
						stages.append(self._resolve_slam(stage))
					case 'nn':
						if stage := self._resolve_nn(cid, stage):
							stages.append(stage)
						else:
							self.log.warning('%s unable to resolve object detection stage %d', cid, i)
					case _:
						# Passthrough
						stages.append(stage)
			except:
				if stage.optional:
					self.log.warning("%s had error in stage %d (%s)", cid, i, stage.stage, exc_info=True)
					continue
				else:
					self.log.exception("%s had error in stage %d (%s)", cid, i, stage.stage)
					raise
		return stages
	
	def process_one(self, camera: CameraConfig, idx: int = 0) -> worker.WorkerInitConfig:
		"Resolve the config for a single camera"
		cid = CameraId(idx, camera.id)
		selector, pose = self._resolve_selector(cid, camera.selector)
		pipeline = self._resolve_pipeline(cid, camera.pipeline)

		if pipeline is None:
			pipeline = []

		return worker.WorkerInitConfig(
			id=camera.id or str(cid),
			selector=selector,
			max_usb=camera.max_usb,
			retry=camera.retry,
			robot_to_camera=camera.pose or pose,
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