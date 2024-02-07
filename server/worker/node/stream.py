from typing import TYPE_CHECKING, Iterable

import depthai as dai

from typedef import pipeline as cfg
from .builder import NodeBuilder, NodeRuntime
from ..msg import AnyCmd, CmdEnableStream, MsgFrame, WorkerMsg

if TYPE_CHECKING:
	from .util import ImageOutStage

class WebStreamNode(NodeRuntime, NodeBuilder[cfg.WebStreamStage]):
	@property
	def requires(self):
		return [
			(f'xout.{self.config.target}', False)
		]

	def handle_command(self, cmd: AnyCmd):
		if isinstance(cmd, CmdEnableStream) and cmd.stream == self.config.target:
			self.log.info(f'Got command: %s %s from %s', "ENABLE" if cmd.enable else "DISABLE", cmd.stream, self.config.name)
			self.enabled = cmd.enable
			return True
		return super().handle_command(cmd)
	
	def start(self, context: NodeRuntime.Context, src: 'ImageOutStage', *args, **kwargs) -> bool:
		src.add_handler(self.handle_frame)
		self.enabled = False
		self.context = context
		return self
	
	def handle_frame(self, frame: dai.ImgFrame):
		if not self.enabled:
			return
		
		self.log.debug(f"Stream %s got frame", self.config.name)
		recv = self.context.clock.now_ns()
		ts = self.context.local_timestamp(frame)
		yield MsgFrame(
			worker='',
			stream=self.config.target,
			timestamp=ts.nanos,
			timestamp_recv=recv,
			sequence=frame.getSequenceNum(),
			data=frame.getCvFrame()
		)

class ShowNode(NodeRuntime, NodeBuilder[cfg.WebStreamStage]):
	do_poll = True
	@property
	def requires(self):
		return [
			(f'xout.{self.config.target}', False)
		]
	
	def start(self, context: NodeRuntime.Context, src: 'ImageOutStage', *args, **kwargs) -> bool:
		src.add_handler(self.handle_frame)
		self.context = context
		self.started = False
		return self
	
	def poll(self, event: str | None = None) -> Iterable[WorkerMsg]:
		if self.started:
			import cv2
			cv2.waitKey(1)
		return None
	
	def handle_frame(self, frame: dai.ImgFrame):
		import cv2
		self.context.local_timestamp(frame)
		cv2.imshow(self.config.target, frame.getCvFrame())
		self.started = True