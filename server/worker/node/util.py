"Utility stages"
from typing import TYPE_CHECKING, Literal, Callable, Iterable, Union

import depthai as dai

from typedef import pipeline as cfg
from .builder import XOutNode, Dependency
from ..msg import WorkerMsg, AnyCmd

if TYPE_CHECKING:
	from .video import MonoCameraNode, ColorCameraNode, DepthBuilder


class TelemetryStage(XOutNode[dai.SystemInformation, cfg.TelemetryStage]):
	"System logger (for telemetry)"
	stream_fps = 2
	stream_name = 'sysinfo'
	
	def get_input(self, pipeline: dai.Pipeline, *args, **kwargs) -> dai.Node.Output:
		syslog = pipeline.createSystemLogger()
		syslog.setRate(1)
		self.node = syslog
		return self.node.out
	
	def handle(self, packet: dai.SystemInformation):
		yield

class ImageOutConfig(cfg._stage_base('xout', implicit=True)):
	target: Literal["left", "right", "rgb", "depth"]
	@property
	def name(self):
		return f'{self.stage}.{self.target}'

class ImageOutStage(XOutNode[dai.ImgFrame, ImageOutConfig]):
	stream_fps = 30

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._handlers = list()
	
	@property
	def stream_name(self):
		return self.config.target
	
	@property
	def requires(self):
		match self.config.target:
			case 'left':
				return [Dependency('mono.left')]
			case 'right':
				return [Dependency('mono.right')]
			case 'rgb':
				return [Dependency('rgb')]
			case 'depth':
				return [Dependency('depth')]
			case _:
				raise RuntimeError()
		
	def get_input(self, pipeline: dai.Pipeline, source: Union['MonoCameraNode', 'ColorCameraNode', 'DepthBuilder'], *args, **kwargs) -> dai.Node.Output:
		# if self.config.syncNN and (self.node_yolo is not None):
		# 	nn = self.node_yolo
		# 	nn.passthrough.link(xoutRgb.input)
		# else:
		# 	color = self.node_rgb
		# 	color.video.link(xoutRgb.input)
		self.source = source
		return source.video_out
	
	def add_handler(self, callback: Callable[[dai.ImgFrame], Iterable[WorkerMsg]]):
		self._handlers.append(callback)
	
	def handle(self, packet: dai.ImgFrame):
		# self.log.info("Stage %s got frame (%s handlers)", self.config.name, len(self._handlers))
		for handler in self._handlers:
			if res := handler(packet):
				yield from res