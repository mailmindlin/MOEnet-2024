"Utility stages"
from typing import TYPE_CHECKING, Literal, Callable, Iterable, Union

import depthai as dai

from typedef import pipeline as cfg
from .builder import XOutNode, Dependency
from ..msg import WorkerMsg, AnyCmd

if TYPE_CHECKING:
	from .video import MonoCameraNode, ColorCameraNode, DepthBuilder


class IMUStage(XOutNode[dai.IMUData, cfg.TelemetryStageConfig]):
	"System logger (for telemetry)"
	stream_name = 'imi'
	
	def get_input(self, pipeline: dai.Pipeline, *args, **kwargs) -> dai.Node.Output:
		syslog = pipeline.createIMU()
		self.node = syslog
		return self.node.out
	
	def handle(self, packet: dai.IMUData):
		return
		yield
