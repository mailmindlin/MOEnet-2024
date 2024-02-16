from typing import TYPE_CHECKING, TypeVar, Generic, Iterable, ClassVar, Optional, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass

import depthai as dai

from typedef import pipeline as pcfg
from ..msg import WorkerMsg, AnyCmd
from ..time import DeviceTimeSync, StampedPacket

if TYPE_CHECKING:
	import logging
	from util.timestamp import Timestamp


T = TypeVar('T')
S = TypeVar('S', bound=pcfg.StageBase)

@dataclass
class Dependency:
	name: str
	optional: bool = False

class StageSkip(BaseException):
	"Raise this exception from a PipelineStage to skip it"
	pass

class XLinkOut(dai.node.XLinkOut, Generic[T]):
	"Typed version of XLinkOut (not a real class)"
	...

class NodeBuilder(Generic[S], ABC):
	stage: ClassVar[str]
	config: S
	
	@classmethod
	def infer(cls, stage, *args: str):
		return None
	
	def __init__(self, config: S, *, log: Optional['logging.Logger'] = None) -> None:
		self.config = config
		self.log = log
	
	requires: list[Dependency] = []
	
	def build(self, pipeline: dai.Pipeline, *args, **kwargs):
		pass

	def start(self, ctx: 'NodeRuntime.Context', *args, **kwargs) -> Optional['NodeRuntime']:
		return None

class NodeRuntime:
	@dataclass
	class Context:
		device: dai.Device
		log: 'logging.Logger'
		tsyn: DeviceTimeSync

		@property
		def clock(self):
			return self.tsyn.reference_clock

		def local_timestamp(self, packet: StampedPacket) -> 'Timestamp':
			return self.tsyn.local_timestamp(packet)
	
	events: list[str] = []
	do_poll: bool = False
	context: Context
	log: 'logging.Logger'

	def __init__(self, *args, context: Context | None = None, **kwargs):
		super().__init__(*args, **kwargs)
		if context is not None:
			self.context = context
			self.log = context.log
	
	def handle_command(self, cmd: AnyCmd):
		return False

	def poll(self, event: str | None = None) -> Iterable[WorkerMsg]:
		return
		# It's a generator
		yield

class XOutRuntime(NodeRuntime, Generic[T], ABC):
	xout_size: int = 1
	xout_blocking: bool = False

	def __init__(self, xout: XLinkOut[T], *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self._xout = xout
		self.queue = self.context.device.getOutputQueue(xout.getStreamName(), maxSize=self.xout_size, blocking=self.xout_blocking)

	@property
	def events(self):
		return [self._xout.getStreamName()]
	
	@abstractmethod
	def handle(self, packet: T):
		pass

	def poll(self, event: str | None = None):
		if packet := self.queue.tryGet():
			return self.handle(packet)


class XOutNode(NodeBuilder[S], NodeRuntime, Generic[T, S], ABC):
	stream_name: str
	stream_fps: int | None = None
	"XOut FPS limit"
	
	xout: XLinkOut[T] | None = None
	"Output node (must be created in build())"

	@property
	def events(self):
		if (xout := self.xout) is not None:
			return [xout.getStreamName()]
		return None
	
	@abstractmethod
	def get_input(self, pipeline: dai.Pipeline, *args, **kwargs) -> dai.Node.Output:
		pass

	def build(self, pipeline: dai.Pipeline, *args, **kwargs):
		source = self.get_input(pipeline, *args, **kwargs)

		self.xout = pipeline.createXLinkOut()
		self.xout.setStreamName(self.stream_name)
		if (fps := self.stream_fps) is not None:
			self.xout.setFpsLimit(fps)
		pipeline.link(source, self.xout.input)

	def start(self, ctx: NodeRuntime.Context, *args, **kwargs):
		stream_name = self.xout.getStreamName()
		self.queue = ctx.device.getOutputQueue(stream_name, maxSize=4, blocking=False)
		self.context = ctx
		return self
	
	@property
	def events(self):
		return [self.xout.getStreamName()]
	
	def handle(self, packet: T):
		pass

	def poll(self, event: str | None = None):
		if packet := self.queue.tryGet():
			return self.handle(packet)

