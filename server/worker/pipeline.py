from typing import Optional, Any, TYPE_CHECKING, Generic, TypeVar, Iterable, Type, Literal, get_args, Callable
from pathlib import Path
from contextlib import contextmanager
from datetime import timedelta

import depthai as dai

from typedef import pipeline as cfg
from .time import DeviceTimeSync
from .node.builder import NodeBuilder, NodeRuntime
from .msg import AnyMsg, AnyCmd, WorkerMsg
from .node.util import ImageOutConfig

if TYPE_CHECKING:
	# import spectacularAI.depthai.Pipeline as SaiPipeline
	import logging

S = TypeVar('S', bound=cfg.PipelineStageWorker)

class MoeNetPipeline:
	"Pipeline builder"
	def __init__(self, config: cfg.PipelineConfigWorker, log: 'logging.Logger'):
		self.log = log.getChild('pipeline')
		self.config = config.root
		self.stages: dict[str, NodeBuilder[cfg.PipelineStageWorker]] = dict()
		self.runtimes: dict[str, NodeRuntime] = dict()
		self.pipeline = dai.Pipeline()
		self._msg_types: dict[str, Type[cfg.PipelineStage]] = dict()
		self.stage_factories: dict[str, Type[NodeBuilder]] = dict()

		self.poll_stages: list[NodeRuntime] = list()
		self.event_targets: dict[str, NodeRuntime] = dict()

		def register(name: str, cfg: Type[S], builder_path: tuple[str]):
			self._msg_types[name] = cfg

			# Stages might have heavy dependencies, so don't load them until/unless necessary
			builder = None
			def lazy_builder(*args, **kwargs):
				nonlocal builder
				if builder is None:
					import importlib
					module = importlib.import_module('.'.join(('', 'node', *builder_path[:-1])), __package__)
					builder = getattr(module, builder_path[-1])
				return builder(*args, **kwargs)
			self.stage_factories[name] = lazy_builder
		
		register('apriltag',  cfg.WorkerAprilTagStageConfig,  ('apriltag', 'AprilTagBuilder'))
		register('slam',      cfg.WorkerSlamStageConfig,      ('slam', 'SlamBuilder'))
		register('mono',      cfg.MonoCameraStageConfig,      ('video', 'MonoCameraNode'))
		register('rgb',       cfg.ColorCameraStageConfig,     ('video', 'ColorCameraNode'))
		register('depth',     cfg.StereoDepthStageConfig,     ('video', 'DepthBuilder'))
		register('telemetry', cfg.TelemetryStageConfig,       ('util', 'TelemetryStage'))
		register('nn',        cfg.ObjectDetectionStageConfig, ('nn', 'ObjectDetectionNode'))
		register('xout',      ImageOutConfig,                 ('util', 'ImageOutStage'))
		register('web',       cfg.WebStreamStageConfig,       ('web', 'WebStreamNode'))
		register('show',      cfg.ShowStageConfig,            ('show', 'ShowNode'))
		
	@contextmanager
	def optional_stage(self, stage: S, optional: Optional[bool] = None):
		if optional is None:
			optional = stage.optional
		try:
			yield
		except:
			if optional:
				self.log.warning("Unable to construct optional stage %s", stage.stage, exc_info=True)
			else:
				self.log.exception("Unable to construct stage %s", stage.stage)
				raise

	def get_configs(self, ty: Type[S]) -> Iterable[S]:
		name = get_args(ty.model_fields['stage'].annotation)[0]
		for stage in self.config.root:
			if stage.stage == name and stage.enabled:
				yield stage
	
	def get_config(self, ty: Type[S], filt: Optional[Callable[[S], bool]] = None) -> Optional[S]:
		stages = self.get_configs(ty)
		if filt:
			stages = filter(filt, stages)
		stages = list(stages)

		if len(stages) == 0:
			return None

		res = stages[0]
		for stage in stages[1:]:
			if stage.optional:
				self.log.warning("Duplicate stage %s (discarding optional)", stage.name)
				continue
			elif res.optional:
				res = stage
				self.log.warning("Duplicate stage %s (discarding optional)", stage.name)
				continue
			else:
				# Collision
				self.log.error("Duplicate stage %s", stage.stage)
				# Newer stage overwrites older one
				res = stage
		return res 
	
	def _config_for_name(self, name: str, optional: bool) -> cfg.PipelineStageWorker:
		for stage_config in self.config:
			if stage_config.name == name:
				return stage_config
		
		# Infer
		parts = name.split('.')
		fname = parts[0]
		try:
			msg_type = self._msg_types[fname]
		except KeyError:
			raise RuntimeError(f"Unknown pipeline stage type '{fname}'")

		if not msg_type.infer:
			raise RuntimeError(f"Unable to infer stage type '{fname}': type {msg_type}")
		
		kwargs = dict()
		#TODO: better solution here
		if len(parts) == 2:
			kwargs['target'] = parts[1]
		
		return msg_type(
			stage=fname,
			optional=optional,
			enabled=True,
			**kwargs,
		)
		
	def _get_stage(self, name: str, optional: bool):
		if cached := self.stages.get(name, None):
			return cached
		#TODO: cache to_build
		try:
			config = self._config_for_name(name, optional)
			return self._build_stage(config, optional)
		except RuntimeError as e:
			if optional:
				return None
			raise RuntimeError(f'Unable to infer config for required stage {name}') from e
	
	def _build_stage(self, config: S, optional: bool):
		# self.log.debug("Build stage %s", config.name)
		try:
			factory = self.stage_factories[config.stage]
			stage_log = self.log.getChild(config.name)
			stage_log.debug("Building with config %s", repr(config))
			stage = factory(config, log=stage_log)

			# Resolve dependencies
			args = list()
			for requirement in stage.requires:
				stage_log.debug("%s stage '%s'", "Prefers" if requirement.optional else "Requires", requirement.name)
				arg = self._get_stage(requirement.name, requirement.optional)
				args.append(arg)
			if stage.build(self.pipeline, *args):
				# Skip stage
				return None
			self.stages[config.name] = stage
			return stage
		except:
			if optional:
				self.log.warning("Optional stage %s failed", config.name, exc_info=True)
			else:
				self.log.exception("Stage %s failed", config.name)
				raise
	def build(self):
		"Build DepthAI pipeline"
		self.log.info("Building pipeline")
		
		for stage_cfg in self.config:
			if stage_cfg.name in self.stages:
				continue
			if not stage_cfg.enabled:
				continue
			self._build_stage(stage_cfg, stage_cfg.optional)
		
		self.log.info("Built pipeline successfully")
		return self.pipeline
	
	def _start_stage(self, name: str, optional: bool):
		if name in self.runtimes:
			return self.stages[name]
		
		try:
			builder = self.stages[name]
		except KeyError:
			if optional:
				return None
			else:
				raise
		
		args = list()
		for requirement in builder.requires:
			arg = self._start_stage(requirement.name, requirement.optional)
			args.append(arg)
		
		ctx = NodeRuntime.Context(
			device=self.device,
			log=self.log.getChild(name),
			tsyn=self.tsyn,
		)
		self.log.info("Starting stage %s", builder.config.name)
		if runtime := builder.start(ctx, *args):
			if runtime.do_poll:
				self.poll_stages.append(runtime)
				self.log.debug("Stage %s requested polling", builder.config.name)
			for event in runtime.events:
				self.event_targets[event] = runtime
			if len(runtime.events) > 0 and self.log:
				self.log.debug("Stage %s registered for events %s", builder.config.name, runtime.events)
		
			self.runtimes[name] = runtime
		else:
			self.runtimes[name] = None
		return builder
	
	def start(self, device: dai.Device):
		"Start pipeline with a device"
		self.device = device
		# device.setLogLevel(dai.LogLevel.DEBUG)
		# device.setLogOutputLevel(dai.LogLevel.DEBUG)
		nodes = self.pipeline.getNodeMap()
		for connections in self.pipeline.getConnectionMap().values():
			for connection in connections:
				src_node = nodes[connection.outputId]
				dst_node = nodes[connection.inputId]
				self.log.debug("Connect %s.%s -> %s.%s", src_node.getName(), connection.outputName, dst_node.getName(), connection.inputName)
		
		self.tsyn = DeviceTimeSync()
		for stage_name in self.stages.keys():
			self.log.debug("Start stage %s", stage_name)
			self._start_stage(stage_name, False)
		
		self.log.debug("Output queues: %s", device.getOutputQueueNames())
	
	def broadcast(self, cmd: AnyCmd):
		handled = False
		for runtime in self.runtimes.values():
			if runtime is not None:
				handled |= runtime.handle_command(cmd)
		return handled
	
	def poll(self):
		already_polled = set()
		if len(self.event_targets) > 0:
			events = self.device.getQueueEvents(list(self.event_targets.keys()), timeout=timedelta(seconds=0.01), maxNumEvents=2)
			if len(events) > 0: self.log.debug("Got events %s", events)
			for event in events:
				if stage := self.event_targets.get(event, None):
					if res := stage.poll(event):
						yield from res
					already_polled.add(stage)
		
		
		for stage in self.poll_stages:
			if stage in already_polled:
				continue # If we processed an event, don't poll again
			if res := stage.poll(None):
				yield from res

	def close(self):
		pass