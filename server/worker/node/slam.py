from typing import Iterable

import depthai as dai
import numpy as np

from typedef import pipeline as cfg
from typedef import apriltag
from typedef.geom import Pose3d, Translation3d, Rotation3d, Quaternion, Twist3d
from typedef.geom_cov import Pose3dCov, Twist3dCov
from util.timestamp import Timestamp
from ..msg import WorkerMsg, AnyCmd, CmdFlush, CmdPoseOverride, MsgOdom

from .builder import NodeBuilder, StageSkip, NodeRuntime
from . import sai_types as sai
# from .sai_types import Pipeline as SaiPipeline, VioSession, Configuration as SaiConfig, CameraPose

class SlamBuilder(NodeBuilder[cfg.WorkerSlamStageConfig]):
	vio_pipeline: sai.Pipeline
	def build(self, pipeline: dai.Pipeline, *args, **kwargs):
		config = self.config
		if not (config.vio or config.slam):
			# What's the point?
			self.log.info("Skipping SLAM (no vio or slam)")
			raise StageSkip()
		
		sai_config = sai.Configuration()
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
		#TODO: pull resolution from RGB config
		sai_config.inputResolution = '800p'
		if mapLoadPath := config.map_load:
			sai_config.mapLoadPath = str(mapLoadPath)
		if mapSavePath := config.map_save:
			sai_config.mapSavePath = str(mapSavePath)
		self.vio_pipeline = sai.Pipeline(pipeline, sai_config)
	
	def start(self, context: NodeRuntime.Context, *args, **kwargs) -> 'SaiSlamRuntime':
		vio_session = self.vio_pipeline.startSession(context.device)
		
		return SaiSlamRuntime(
			self,
			context,
			vio_session,
		)

def sai_camera_pose(cam: 'sai.CameraPose') -> Pose3d:
	"Convert camera pose to WPI pose"
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
	

class SaiSlamRuntime(NodeRuntime):
	do_poll = True
	
	events = [
		# 'spectacularAI_depth',
		# 'spectacularAI_primaryScript',
		# 'spectacularAI_trackedFeatures',
		'spectacularAI_imu',
		# 'spectacularAI_secondaryScript'
	]
	
	def __init__(self, builder: SlamBuilder, context: NodeRuntime.Context, vio_session: 'sai.Session'):
		super().__init__(context=context)
		self.vio_session = vio_session
		self._vio_last_tag = 0
		"Last tag recieved from SAI"
		self._vio_require_tag = 0
		"Tag required by last flush"

		if builder.config.waitForPose:
			self._vio_require_tag = 1
	
	def handle_command(self, cmd: AnyCmd):
		if isinstance(cmd, CmdFlush):
			self._vio_require_tag += 1
			dev_ts = self.context.tsyn.dev_clock.now()
			self.vio_session.addTrigger(dev_ts.as_seconds(), self._vio_require_tag)
			return True
		elif isinstance(cmd, CmdPoseOverride):
			self.log.warning("Override SLAM pose")
			# Convert to SAI pose
			if cmd.timestamp is None:
				ts = self.context.clock.now()
			else:
				ts = Timestamp.from_nanos(cmd.timestamp, clock=self.context.clock)
			
			ts_sai = self.context.tsyn.wall_to_device(ts)

			if isinstance(cmd.pose, Pose3d):
				pose = cmd.pose
				pose_cov = np.zeros((3,3), dtype=float)
				rot_cov = 0
			else:
				pose = cmd.pose.mean
				raw_cov = cmd.pose.cov
				pose_cov = raw_cov[:3, :3]
				rot_cov = 0 # TODO
			
			# Use AprilTag conversion utils so we don't write this again
			fake_at = apriltag.AprilTagWpi(ID=0, pose=pose) \
				.to_sai(apriltag.AprilTagFamily.TAG_16H5, 1.0)
			fake_mat = fake_at.get_sai_matrix()
			
			pose_sai = sai.Pose.fromMatrix(
				ts_sai,
				fake_mat
			)

			self.vio_session.addAbsolutePose(pose_sai, pose_cov, rot_cov)
			# Add trigger
			self.vio_session.addTrigger(ts_sai, self._vio_require_tag)
			return True
		else:
			return super().handle_command(cmd)
	
	def poll(self, event: str | None = None) -> Iterable[WorkerMsg]:
		for _ in range(10):
			if not self.vio_session.hasOutput():
				return
			
			vio_out = self.vio_session.getOutput()

			if vio_out.tag > 0:
				self.log.info("Got tagged output %s", vio_out.tag)
				self._vio_last_tag = vio_out.tag
			
			# Ensure we've completed all VIO flushes
			if self._vio_last_tag < self._vio_require_tag:
				self.log.info("Skipped vio frame (bad tag) %s %s", self._vio_last_tag, self._vio_require_tag)
				return
			
			# SAI uses device-time, so we have to do some conversion
			timestamp = self.context.tsyn.device_to_wall(vio_out.pose.time)
			self.log.debug("Pose trail: %d t0=%s ct=%s dai=%s", len(vio_out.poseTrail), vio_out.poseTrail[0].time if vio_out.poseTrail else -1, self.context.tsyn.dev_clock.now().as_seconds(), self.context.tsyn.dai_clock.now().as_seconds())

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
				#TODO: define which camera we want
				# sai_camera_pose(self.vio_session.getRgbCameraPose(vio_out)),
				sai_camera_pose(vio_out.getCameraPose(0)),
				pose_cov
			)

			twist_cov = np.zeros((6, 6), dtype=np.float32)
			twist_cov[:3,:3] = np.asarray(vio_out.velocityCovariance)
			twist_cov[3:,3:] = np.eye(3) * ANG_VEL_COV
			twist = Twist3dCov(
				Twist3d(
					# velocity is m/s
					dx = vio_out.velocity.x,
					dy = vio_out.velocity.y,
					dz = vio_out.velocity.z,
					# angularVelocity is in rad/s
					rx = vio_out.angularVelocity.x,
					ry = vio_out.angularVelocity.y,
					rz = vio_out.angularVelocity.z,
				),
				twist_cov
			)

			yield MsgOdom(
				timestamp=timestamp.nanos,
				pose=pose,
				twist=twist,
			)