from typing import TYPE_CHECKING, Iterable

import depthai as dai
import numpy as np

from .builder import NodeBuilder, StageSkip, NodeRuntime
from typedef import pipeline as cfg
from typedef.geom import Pose3d, Translation3d, Rotation3d, Quaternion, Twist3d
from ..msg import WorkerMsg, AnyCmd, CmdFlush, MsgPose
if TYPE_CHECKING:
	from datetime import timedelta
	from typedef.sai_types import Pipeline as SaiPipeline, VioSession

class SlamBuilder(NodeBuilder[cfg.SlamStageWorker]):
	vio_pipeline: 'SaiPipeline'
	def build(self, pipeline: dai.Pipeline, *args, **kwargs):
		config = self.config
		if not (config.vio or config.slam):
			# What's the point?
			self.log.info("Skipping SLAM (no vio or slam)")
			raise StageSkip()
		
		import spectacularAI as sai
		sai_config = sai.depthai.Configuration()
		if config.slam and (apriltags := config.apriltags):
			sai_config.aprilTagPath = str(apriltags.path)
		sai_config.internalParameters = {
			# "ffmpegVideoCodec": "libx264 -crf 15 -preset ultrafast",
			# "computeStereoPointCloud": "true",
			# "computeDenseStereoDepthKeyFramesOnly": "true",
			"alreadyRectified": "true"
		}
		sai_config.useSlam = config.slam
		sai_config.useFeatureTracker = True
		sai_config.useVioAutoExposure = True
		sai_config.inputResolution = '800p'
		self.vio_pipeline = sai.depthai.Pipeline(pipeline.pipeline, sai_config)
	
	def start(self, device: dai.Device, *args, **kwargs) -> 'SlamRuntime':
		self.vio_session = self.vio_pipeline.startSession(device)
		
		return True

class SlamRuntime(NodeRuntime):
	do_poll = True
	
	def __init__(self, builder: SlamBuilder, context: NodeRuntime.Context, vio_session: 'VioSession'):
		super().__init__(context=context)
		self.vio_session = vio_session
		self._vio_last_tag = 0
		self._vio_require_tag = 0
	
	def handle_command(self, cmd: AnyCmd):
		if isinstance(cmd, CmdFlush):
			dai_ts: 'timedelta' = dai.Clock.now()
			self._vio_require_tag += 1
			dev_ts = dai_ts.total_seconds() - self._offset_dev_to_dai
			self.vio_session.addTrigger(dev_ts, self._vio_require_tag)
			return True
		return super().handle_command(cmd)
	
	def poll(self, event: str | None = None) -> Iterable[WorkerMsg]:
		if not self.vio_session.hasOutput():
			return
		
		vio_out = self.vio_session.getOutput()

		if vio_out.tag > 0:
			self._vio_last_tag = vio_out.tag
		
		# Ensure we've completed all VIO flushes
		if self._vio_last_tag < self._vio_require_tag:
			self.log.info("Skipped vio frame")
			return

		pc = np.asarray(vio_out.positionCovariance)
		vc = np.asarray(vio_out.velocityCovariance)

		# SAI uses device-time, so we have to do some conversion
		latency = dai.Clock.now() - timedelta(seconds=vio_out.pose.time)
		timestamp = int(vio_out.pose.time * 1e9)

		# Why is orientation covariance 1e-4?
		# Because I said so
		ROTATION_COV = 1e-4
		ANG_VEL_COV = 1e-3

		yield MsgPose(
			timestamp=timestamp,
			# Not sure if we need this property
			view_mat=vio_out.pose.asMatrix(),
			# I wish there was a better way to do this, but spectacularAI types are native wrappers,
			# and they can't be nicely shared between processes
			pose=Pose3d(
				translation=Translation3d(
					x = vio_out.pose.position.x,
					y = vio_out.pose.position.y,
					z = vio_out.pose.position.z,
				),
				rotation=Rotation3d(Quaternion(
					w = vio_out.pose.orientation.w,
					x = vio_out.pose.orientation.x,
					y = vio_out.pose.orientation.y,
					z = vio_out.pose.orientation.z,
				))
			),
			poseCovariance=np.asarray([
				[pc[0, 0], pc[0, 1], pc[0, 2], 0, 0, 0],
				[pc[1, 0], pc[1, 1], pc[1, 2], 0, 0, 0],
				[pc[2, 0], pc[2, 1], pc[2, 2], 0, 0, 0],
				[0, 0, 0, ROTATION_COV, 0, 0],
				[0, 0, 0, 0, ROTATION_COV, 0],
				[0, 0, 0, 0, 0, ROTATION_COV],
			], dtype=np.float32),
			twist=Twist3d(
				dx = vio_out.velocity.x,
				dy = vio_out.velocity.y,
				dz = vio_out.velocity.z,
				rx = vio_out.angularVelocity.x,
				ry = vio_out.angularVelocity.y,
				rz = vio_out.angularVelocity.z,
			),
			twistCovariance=np.asarray([
				[vc[0, 0], vc[0, 1], vc[0, 2], 0, 0, 0],
				[vc[1, 0], vc[1, 1], vc[1, 2], 0, 0, 0],
				[vc[2, 0], vc[2, 1], vc[2, 2], 0, 0, 0],
				[0, 0, 0, ANG_VEL_COV, 0, 0],
				[0, 0, 0, 0, ANG_VEL_COV, 0],
				[0, 0, 0, 0, 0, ANG_VEL_COV],
			], dtype=np.float32),
		)