from typing import TYPE_CHECKING, TypeVar, Optional
from abc import ABC, abstractproperty

import depthai as dai

from typedef import pipeline as cfg
from .builder import NodeBuilder, NodeRuntime

if TYPE_CHECKING:
	from .slam import SlamBuilder


S = TypeVar('S', bound=cfg.PipelineStageWorker)
class VideoBuilder(NodeBuilder[S], ABC):
	node: dai.node.ColorCamera | dai.node.MonoCamera | dai.node.StereoDepth
	
	@abstractproperty
	def camera_socket(self) -> dai.CameraBoardSocket: ...
	
	@abstractproperty
	def video_out(self) -> dai.Node.Output: ...

	def start(self, ctx: NodeRuntime.Context, *args, **kwargs) -> NodeRuntime | None:
		return None


class MonoBuilder(VideoBuilder[cfg.MonoConfigStage]):
	node: dai.node.MonoCamera
	@classmethod
	def infer(cls, name: str):
		target = name.lstrip('mono.')
		return cfg.MonoConfigStage(stage='mono', target=target)
	
	requires = [('slam', True)]

	@property
	def video_out(self):
		return self.node.out
	
	@property
	def camera_socket(self) -> dai.CameraBoardSocket:
		match self.config.target:
			case 'left':
				return dai.CameraBoardSocket.LEFT
			case 'right':
				return dai.CameraBoardSocket.RIGHT
			case _:
				raise ValueError()
	
	def build(self, pipeline: dai.Pipeline, slam: Optional['SlamBuilder'] = None, *args, **kwargs):
		if slam is not None:
			match self.config.target:
				case 'left':
					node = slam.vio_pipeline.monoLeft
				case 'right':
					node = slam.vio_pipeline.monoRight
				case _:
					raise RuntimeError()
		else:
			node = pipeline.createMonoCamera()
			node.setFps(self.config.fps or 120)
			node.setBoardSocket(self.camera_socket)
			node.setResolution(self.config.resolution or dai.MonoCameraProperties.SensorResolution.THE_400_P)
		self.node = node


class RgbBuilder(VideoBuilder[cfg.RgbConfigStage]):
	node: dai.node.ColorCamera
	@classmethod
	def infer(cls, name: str):
		return cfg.RgbConfigStage(stage='rgb')

	requires = [('slam', True)]
	
	def build(self, pipeline: dai.Pipeline, slam: Optional['SlamBuilder'] = None, *args, **kwargs):
		if slam is not None:
			if (color := getattr(slam.vio_pipeline, 'color', None)) is not None:
				color: dai.node.ColorCamera
				self.node = color
				return
		
		camRgb = pipeline.createColorCamera()
		camRgb.setPreviewSize(416, 416)
		
		camRgb.setResolution(self.config.resolution or dai.ColorCameraProperties.SensorResolution.THE_4_K)
		camRgb.setInterleaved(False)
		camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
		self.node = camRgb
	
	camera_socket = dai.CameraBoardSocket.RGB

	@property
	def video_out(self):
		return self.node.video

class DepthBuilder(VideoBuilder[cfg.DepthConfigStage]):
	node: dai.node.StereoDepth
	camera_socket = None #TODO: fix inheritance so we can get rid of this method
	requires = [
		('mono.left', False),
		('mono.right', False),
	]
	
	def build(self, pipeline: dai.Pipeline, left: MonoBuilder, right: MonoBuilder, *args, **kwargs):
		# if (slam is not None) and False:
		#     node = slam.vio_pipeline.stereo
		#     # node.setDepthAlign(dai.CameraBoardSocket.RGB)
		#     return node
		
		stereo = pipeline.createStereoDepth()
		stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)

		# Align depth map to the perspective of RGB camera, on which inference is done
		stereo.setDepthAlign(dai.CameraBoardSocket.RGB)

		monoLeft = left
		monoRight = right
		stereo.setOutputSize(monoRight.node.getResolutionWidth(), monoRight.node.getResolutionHeight())

		# Linking
		monoLeft.node.out.link(stereo.left)
		monoRight.node.out.link(stereo.right)
		self.node = stereo
	
	@property
	def video_out(self):
		return self.node.depth
