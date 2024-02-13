from typing import TYPE_CHECKING, cast, Iterable

import depthai as dai
import numpy as np

from .builder import NodeBuilder, StageSkip, NodeRuntime
from typedef import pipeline as cfg
from typedef.geom import Pose3d, Translation3d, Rotation3d, Quaternion, Twist3d
from typedef.geom_cov import Pose3dCov, Twist3dCov
from ..msg import WorkerMsg, AnyCmd, CmdFlush, MsgOdom
if TYPE_CHECKING:
	from typedef.sai_types import Pipeline as SaiPipeline, VioSession, Configuration as SaiConfig, CameraPose
else:
	SaiConfig = None

class SlamBuilder(NodeBuilder[cfg.SlamStageWorker]):
	vio_pipeline: 'SaiPipeline'
	def build(self, pipeline: dai.Pipeline, *args, **kwargs):
		config = self.config
		if not (config.vio or config.slam):
			# What's the point?
			self.log.info("Skipping SLAM (no vio or slam)")
			raise StageSkip()
		
		import spectacularAI as sai
		sai_config = cast(SaiConfig, sai.depthai.Configuration())
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
		if mapLoadPath := config.map_load:
			sai_config.mapLoadPath = str(mapLoadPath)
		if mapSavePath := config.map_save:
			sai_config.mapSavePath = str(mapSavePath)
		self.vio_pipeline = sai.depthai.Pipeline(pipeline, sai_config)
	
	def start(self, device: dai.Device, *args, **kwargs) -> 'SlamRuntime':
		self.vio_session = self.vio_pipeline.startSession(device)
		
		return True

def sai_camera_pose(cam: 'CameraPose') -> Pose3d:
	pose_cv2 = Pose3d(
		translation=Translation3d(
			x = cam.pose.position.x,
			y = cam.pose.position.y,
			z = cam.pose.position.z,
		),
		rotation=Rotation3d(Quaternion(
			w = cam.pose.orientation.w,
			x = cam.pose.orientation.x,
			y = cam.pose.orientation.y,
			z = cam.pose.orientation.z,
		))
	)
	return pose_cv2
	

class SlamRuntime(NodeRuntime):
	do_poll = True
	
	def __init__(self, builder: SlamBuilder, context: NodeRuntime.Context, vio_session: 'VioSession'):
		super().__init__(context=context)
		self.vio_session = vio_session
		self._vio_last_tag = 0
		self._vio_require_tag = 0
	
	def handle_command(self, cmd: AnyCmd):
		if isinstance(cmd, CmdFlush):
			self._vio_require_tag += 1
			dev_ts = self.context.tsyn.dev_clock.now()
			self.vio_session.addTrigger(dev_ts.as_seconds(), self._vio_require_tag)
			return True
		return super().handle_command(cmd)
	
	def poll(self, event: str | None = None) -> Iterable[WorkerMsg]:
		if not self.vio_session.hasOutput():
			return
		
		vio_out = self.vio_session.getOutput()

		if vio_out.tag > 0:
			self.log.info("Got tagged output %s", vio_out.tag)
			self._vio_last_tag = vio_out.tag
		
		# Ensure we've completed all VIO flushes
		if self._vio_last_tag < self._vio_require_tag:
			self.log.info("Skipped vio frame")
			return
		
		# SAI uses device-time, so we have to do some conversion
		timestamp = self.context.tsyn.device_to_wall(vio_out.pose.time)
		self.log.info("Pose trail: %d %s %s", len(vio_out.poseTrail), vio_out.poseTrail[0].time if vio_out.poseTrail else -1, self.context.tsyn.dev_clock.now().as_seconds())
		self.context.tsyn.dev_clock

		# Why is orientation covariance 1e-4?
		# Because I said so
		ROTATION_COV = 1e-4
		ANG_VEL_COV = 1e-3

		# I wish there was a better way to do this, but spectacularAI types are native wrappers,
		# and they can't be nicely shared between processes
		pose_cov = np.zeros((6, 6), dtype=np.float32)
		pose_cov[:3,:3] = np.asarray(vio_out.positionCovariance)
		pose_cov[3:,3:] = np.eye(3) * ROTATION_COV
		pose = Pose3dCov(
			sai_camera_pose(self.vio_session.getRgbCameraPose(vio_out)),
			pose_cov
		)

		twist_cov = np.zeros((6, 6), dtype=np.float32)
		twist_cov[:3,:3] = np.asarray(vio_out.velocityCovariance)
		twist_cov[3:,3:] = np.eye(3) * ANG_VEL_COV
		twist = Twist3dCov(
			Twist3d(
				dx = vio_out.velocity.x,
				dy = vio_out.velocity.y,
				dz = vio_out.velocity.z,
				rx = vio_out.angularVelocity.x,
				ry = vio_out.angularVelocity.y,
				rz = vio_out.angularVelocity.z,
			),
			twist_cov
		)

		yield MsgOdom(
			timestamp=timestamp,
			pose=pose,
			twist=twist,
		)