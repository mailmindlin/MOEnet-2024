from typing import TYPE_CHECKING, Iterable

import depthai as dai
import cv2

from typedef import pipeline as cfg
from .builder import NodeBuilder, NodeRuntime, Dependency
from ..msg import WorkerMsg

if TYPE_CHECKING:
	from .util import ImageOutStage

class ShowNode(NodeRuntime, NodeBuilder[cfg.WebStreamStageConfig]):
	do_poll = True
	@property
	def requires(self):
		return [Dependency(f'xout.{self.config.target}')]
	
	def start(self, context: NodeRuntime.Context, src: 'ImageOutStage', *args, **kwargs) -> bool:
		src.add_handler(self.handle_frame)
		self.context = context
		self.started = False
		return self
	
	def poll(self, event: str | None = None) -> Iterable[WorkerMsg]:
		if self.started:
			cv2.waitKey(1)
		return None
	
	def handle_frame(self, frame: dai.ImgFrame):
		self.context.local_timestamp(frame)
		cv2.imshow(self.config.target, frame.getCvFrame())
		self.started = True