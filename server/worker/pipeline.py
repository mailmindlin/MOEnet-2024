from typing import Optional, Any, TYPE_CHECKING, Generic, TypeVar, Iterable, Type, Literal, get_args, Callable
from pathlib import Path
from contextlib import contextmanager
from datetime import timedelta

import depthai as dai

from typedef import pipeline as cfg
from .time import DeviceTimeSync
from .node.builder import NodeBuilder, NodeRuntime
from .msg import AnyMsg, AnyCmd, WorkerMsg
from .node.apriltag import AprilTagBuilder
from .node.nn import ObjectDetectionNode
from .node.slam import SlamBuilder
from .node.stream import WebStreamNode, ShowNode
from .node.util import ImageOutStage, TelemetryStage, ImageOutConfig
from .node.video import MonoBuilder, RgbBuilder, DepthBuilder

if TYPE_CHECKING:
	# import spectacularAI.depthai.Pipeline as SaiPipeline
	import logging

S = TypeVar('S', bound=cfg.PipelineStageWorker)

class MoeNetPipeline:
	"Pipeline builder"
	def __init__(self, config: list[cfg.PipelineStageWorker], log: 'logging.Logger'):
		self.log = log
		self.config = config
		self.stages: dict[str, NodeBuilder[cfg.PipelineStageWorker]] = dict()
		self.runtimes: dict[str, NodeRuntime] = dict()
		self.pipeline = dai.Pipeline()
		self._msg_types: dict[str, Type[cfg.PipelineStage]] = dict()
		self.stage_factories: dict[str, Type[NodeBuilder]] = dict()

		self.poll_stages: list[NodeRuntime] = list()
		self.event_targets: dict[str, NodeRuntime] = dict()

		def register(name: str, builder: Type[NodeBuilder], cfg: Type[S]):
			self._msg_types[name] = cfg
			self.stage_factories[name] = builder
		
		register('apriltag',  AprilTagBuilder, cfg.ApriltagStageWorker)
		register('slam',      SlamBuilder, cfg.SlamStageWorker)
		register('mono',      MonoBuilder, cfg.MonoConfigStage)
		register('rgb',       RgbBuilder, cfg.RgbConfigStage)
		register('depth',     DepthBuilder, cfg.DepthConfigStage)
		register('telemetry', TelemetryStage, cfg.TelemetryStage)
		register('nn',        ObjectDetectionNode, cfg.ObjectDetectionStage)
		register('xout',      ImageOutStage, ImageOutConfig)
		register('web',       WebStreamNode, cfg.WebStreamStage)
		register('show',      ShowNode, cfg.ShowStage)
		
		self.build()
	
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
	
	def _config_for_name(self, name: str, optional: bool) -> cfg.PipelineStage:
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
		self.log.debug("Build stage %s", config.name)
		try:
			factory = self.stage_factories[config.stage]
			self.log.debug("Stage %s (%s) using factory %s", config.name, repr(config), factory)
			stage = factory(config, log=self.log.getChild(config.name))
			args = list()
			for requirement, req_optional in stage.requires:
				self.log.debug("Stage %s %s %s", config.name, "prefers" if req_optional else "requires", requirement)
				arg = self._get_stage(requirement, req_optional)
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
				self.log.exception("Stage %s failed")
				raise
	def build(self):
		"Build DepthAI pipeline"
		for stage_cfg in self.config:
			if stage_cfg.name in self.stages:
				continue
			if not stage_cfg.enabled:
				continue
			self._build_stage(stage_cfg, stage_cfg.optional)
		
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
		for requirement, req_optional in builder.requires:
			arg = self._start_stage(requirement, req_optional)
			args.append(arg)
		
		ctx = NodeRuntime.Context(
			device=self.device,
			log=self.log.getChild(name),
			tsyn=self.tsyn,
		)
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