from typing import TYPE_CHECKING, Optional

import depthai as dai

from typedef import pipeline as cfg
from .builder import NodeBuilder, NodeRuntime, Dependency
from ..msg import AnyCmd, CmdEnableStream, MsgFrame

if TYPE_CHECKING:
	from .util import ImageOutStage

class WebStreamNode(NodeRuntime, NodeBuilder[cfg.WebStreamStageConfig]):
	@property
	def requires(self):
		return [Dependency(f'xout.{self.config.target}')]

	def handle_command(self, cmd: AnyCmd):
		if isinstance(cmd, CmdEnableStream) and cmd.stream == self.config.target:
			self.log.info(f'Got command: %s %s from %s', "ENABLE" if cmd.enable else "DISABLE", cmd.stream, self.config.name)
			self.enabled = cmd.enable
			return True
		return super().handle_command(cmd)
	
	def start(self, context: NodeRuntime.Context, src: 'ImageOutStage', *args, **kwargs) -> Optional[NodeRuntime]:
		src.add_handler(self.handle_frame)
		self.enabled = False
		self.context = context
		return self
	
	def handle_frame(self, frame: dai.ImgFrame):
		ts = self.context.local_timestamp(frame)
		if not self.enabled:
			return
		
		self.log.debug(f"Stream %s got frame", self.config.name)
		recv = self.context.clock.now_ns()
		yield MsgFrame(
			worker='',
			stream=self.config.target,
			timestamp=ts.nanos,
			timestamp_recv=recv,
			sequence=frame.getSequenceNum(),
			data=frame.getCvFrame()
		)
