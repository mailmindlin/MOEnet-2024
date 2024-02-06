from typing import Optional, Any, TYPE_CHECKING, Generic, TypeVar, Iterable, Type, Literal, get_args, Callable
from pathlib import Path
from contextlib import contextmanager
from datetime import timedelta

import depthai as dai
import numpy as np
import cv2
from depthai import Device, Pipeline
from robotpy_apriltag import AprilTagDetector, AprilTagDetection, AprilTagPoseEstimator, AprilTagFieldLayout

from typedef import pipeline as ps
from .msg import AnyMsg, MsgPose, AnyCmd, CmdEnableStream, CmdFlush
from typedef.geom import Pose3d, Translation3d, Rotation3d, Quaternion, Twist3d
from typedef.pipeline import PipelineStageWorker as PipelineStageConfig

if TYPE_CHECKING:
	# import spectacularAI.depthai.Pipeline as SaiPipeline
	import logging
	from typedef.sai_types import Pipeline as SaiPipeline

T = TypeVar('T')
S = TypeVar('S', bound=ps.PipelineStageWorker)

class StageSkip(BaseException):
	pass

class XLinkOut(dai.node.XLinkOut, Generic[T]):
	"Typed version of XLinkOut (not a real class)"
	...

class QueueLike(Generic[T]):
	def has(self):
		return False
	def get(self) -> T:
		raise RuntimeError()
	def tryGet(self) -> Optional[T]:
		return None
	def tryGetAll(self) -> list[T]:
		return list()


class PipelineStage(Generic[S]):
	@classmethod
	def infer(cls, name: str):
		return None
	
	def __init__(self, config: S, *, log: Optional['logging.Logger'] = None) -> None:
		self.config = config
		self.log = log
	
	requires: list[tuple[str, bool]] = []
	events: Optional[list[str]] = None

	def handle_command(self, cmd: AnyCmd):
		pass
	
	def build(self, pipeline: dai.Pipeline, *args, **kwargs):
		pass

	def start(self, device: dai.Device, *args, **kwargs) -> bool:
		return True
	
	def poll(self, event: Optional[str] = None) -> Iterable[AnyMsg]:
		return
		yield


class DataPipelineStage(PipelineStage[S], Generic[T, S]):
	xout: XLinkOut[T]

	def start(self, device: Device, *args, **kwargs):
		stream_name = self.xout.getStreamName()
		self.queue = device.getOutputQueue(stream_name, maxSize=4, blocking=False)
		return False
	
	@property
	def events(self):
		return [self.xout.getStreamName()]
	
	def handle(self, packet: T):
		pass

	def poll(self, event: Optional[str] = None):
		if packet := self.queue.tryGet():
			return self.handle(packet)


class SlamStage(PipelineStage[ps.SlamStageWorker]):
	vio_pipeline: 'SaiPipeline'
	def build(self, pipeline: dai.Pipeline, *args, **kwargs):
		config = self.config
		if not (config.vio or config.slam):
			# What's the point?
			if self.log: self.log.info("Skipping SLAM (no vio or slam)")
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
	
	def start(self, device: Device, *args, **kwargs) -> bool:
		self.vio_session = self.vio_pipeline.startSession(device)
		self._vio_last_tag = 0
		self._vio_require_tag = 0
		return True
	
	def poll(self, event: str | None = None) -> Iterable[AnyMsg]:
		if not self.vio_session.hasOutput():
			return
		
		vio_out = self.vio_session.getOutput()

		if vio_out.tag > 0:
			self._vio_last_tag = vio_out.tag
		
		# Ensure we've completed all VIO flushes
		if self._vio_last_tag < self._vio_require_tag:
			if self.log: self.log.info("Skipped vio frame")
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

class MonoStage(PipelineStage[ps.MonoConfigStage]):
	@classmethod
	def infer(cls, name: str):
		target = name.lstrip('mono.')
		return ps.MonoConfigStage(stage='mono', target=target)
	
	requires = [('slam', True)]
	
	def build(self, pipeline: dai.Pipeline, slam: Optional['SlamStage'] = None, *args, **kwargs):
		if slam is not None:
			if self.config.target == 'left':
				node = slam.vio_pipeline.monoLeft
			elif self.config.target == 'right':
				node = slam.vio_pipeline.monoRight
			else:
				raise RuntimeError()
		else:
			node = pipeline.createMonoCamera()
			node.setFps(120)
			node.setBoardSocket(self.camera_socket)
			node.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
		self.node = node
	
	@property
	def camera_socket(self):
		return dai.CameraBoardSocket.LEFT if self.config.target == 'left' else dai.CameraBoardSocket.RIGHT
	
	@property
	def video_out(self):
		return self.node.out
	
	def start(self, device: Device, *args):
		return False

class RgbStage(PipelineStage):
	@classmethod
	def infer(cls, name: str):
		return ps.RgbConfigStage(stage='rgb')

	requires = [('slam', True)]
	
	def build(self, pipeline: dai.Pipeline, slam: Optional['SlamStage'] = None, *args, **kwargs):
		if (slam is not None) and (getattr(slam.vio_pipeline, 'color', None) is not None):
			self.node: dai.node.ColorCamera = slam.vio_pipeline.color
			return
		
		camRgb = pipeline.createColorCamera()
		camRgb.setPreviewSize(416, 416)
		camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_4_K)
		camRgb.setInterleaved(False)
		camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
		self.node = camRgb
	
	camera_socket = dai.CameraBoardSocket.RGB

	def start(self, device: Device, *args, **kwargs) -> bool:
		return False

	@property
	def video_out(self):
		return self.node.video

class DepthStage(PipelineStage[ps.DepthConfigStage]):
	@classmethod
	def infer(cls, name: str):
		return ps.DepthConfigStage(stage='depth')
	
	requires = [
		('mono.left', False),
		('mono.right', False),
	]
	
	def build(self, pipeline: dai.Pipeline, left: MonoStage, right: MonoStage, *args, **kwargs):
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
	
	def start(self, device: Device, *args, **kwargs) -> bool:
		return False
	
	@property
	def video_out(self):
		return self.node.depth

class TelemetryStage(DataPipelineStage[dai.SystemInformation, ps.TelemetryStage]):
	"System logger (for telemetry)"
	def build(self, pipeline: Pipeline, *args, **kwargs):
		syslog = pipeline.createSystemLogger()
		syslog.setRate(1)
		self.node = syslog

		xout = pipeline.createXLinkOut()
		xout.setStreamName('sysinfo')
		xout.setFpsLimit(2)
		syslog.out.link(xout)
		self.xout = xout
	
	def handle(self, packet: dai.SystemInformation):
		yield

class ImageXOutConfig(ps.StageBase):
	stage: Literal["out"]
	target: Literal["left", "right", "rgb", "depth"]
	@property
	def name(self):
		return f'{self.stage}.{self.target}'

class ImageOutStage(DataPipelineStage[dai.ImgFrame, ImageXOutConfig]):
	@classmethod
	def infer(cls, name: str):
		return ImageXOutConfig(stage='out', target=name.lstrip('out.'))
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._handlers = list()
	
	@property
	def requires(self):
		if self.config.target == 'left':
			return [('mono.left', False)]
		elif self.config.target == 'right':
			return [('mono.right', False)]
		elif self.config.target == 'rgb':
			return [('rgb', False)]
		elif self.config.target == 'left':
			return [('depth', False)]
		else:
			raise RuntimeError()
	
	def add_handler(self, callback: Callable[[dai.ImgFrame], Iterable[AnyMsg]]):
		self._handlers.append(callback)
	
	def build(self, pipeline: dai.Pipeline, source: MonoStage | RgbStage | DepthStage, *args, **kwargs):
		xout = pipeline.createXLinkOut()
		self.source = source

		# if self.config.syncNN and (self.node_yolo is not None):
		# 	nn = self.node_yolo
		# 	nn.passthrough.link(xoutRgb.input)
		# else:
		# 	color = self.node_rgb
		# 	color.video.link(xoutRgb.input)

		xout.setStreamName(self.config.target)
		xout.setFpsLimit(30)
		source.video_out.link(xout.input)
		self.xout = xout
	
	def handle(self, packet: dai.ImgFrame):
		for handler in self._handlers:
			if res := handler(packet):
				yield from res

class ObjectDetectionStage(PipelineStage[ps.ObjectDetectionStage]):
	requires = [
		('rgb', False),
		('depth', False),
	]
	
	def build(self, pipeline: Pipeline, rgb: RgbStage, depth: DepthStage, *args, **kwargs):
		spatialDetectionNetwork = pipeline.createYoloSpatialDetectionNetwork()
		nnConfig = self.config.config
		nnBlobPath = Path(self.config.blobPath).resolve().absolute()
		if not nnBlobPath.exists():
			raise RuntimeError(f"nnBlobPath not found: {nnBlobPath}")
		spatialDetectionNetwork.setBlobPath(nnBlobPath)
		spatialDetectionNetwork.input.setBlocking(False)

		spatialDetectionNetwork.setConfidenceThreshold(nnConfig.confidence_threshold)
		spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)
		spatialDetectionNetwork.setDepthLowerThreshold(nnConfig.depthLowerThreshold)
		spatialDetectionNetwork.setDepthUpperThreshold(nnConfig.depthUpperThreshold)

		# Yolo specific parameters
		spatialDetectionNetwork.setNumClasses(nnConfig.classes)
		spatialDetectionNetwork.setCoordinateSize(nnConfig.coordinateSize)
		spatialDetectionNetwork.setAnchors(nnConfig.anchors)
		spatialDetectionNetwork.setAnchorMasks(nnConfig.anchor_masks)
		spatialDetectionNetwork.setIouThreshold(nnConfig.iou_threshold)
		self.labels = nnConfig.labels

		# Linking
		rgb.node.preview.link(spatialDetectionNetwork.input)

		depth.node.depth.link(spatialDetectionNetwork.inputDepth)
		
		self.node = spatialDetectionNetwork

		xout = pipeline.createXLinkOut()
		xout.setStreamName('nn')
		spatialDetectionNetwork.out.link(xout.input)
		self.xout = xout

class WebStreamStage(PipelineStage[ps.WebStreamStage]):
	@property
	def requires(self):
		return [
			(f'out.{self.config.target}', False)
		]

	def handle_command(self, cmd: AnyCmd):
		if isinstance(cmd, CmdEnableStream) and cmd.stream == self.config.target:
			if self.log: self.log.info(f'Got command: {"ENABLE" if cmd.enable else "DISABLE"} %s', cmd.stream)
			self.enabled = cmd.enable
			return
		return super().handle_command(cmd)
	
	def start(self, device: Device, src: ImageOutStage, *args, **kwargs) -> bool:
		src.add_handler(self.handle_frame)
		self.enabled = False
		return False
	
	def handle_frame(self, frame: dai.ImgFrame):
		if not self.enabled:
			return
		
		if self.log: self.log.info(f"Stream {self.config.name} got frame")
		pass


class AprilTagStage(PipelineStage[ps.ApriltagStageWorker]):
	@property
	def requires(self):
		if self.config.runtime == 'host':
			return [
				(f'out.{self.config.camera}', False)
			]
		else:
			if self.config.camera == 'rgb':
				return [('rgb', False)]
			else:
				return [(f'mono.{self.config.camera}', False)]
	
	def build_device(self, pipeline: Pipeline, src: RgbStage | MonoStage):
		node = pipeline.createAprilTag()
		src.video_out.link(node.inputImage)
		self.node = node

		xout = pipeline.createXLinkOut()
		xout.setStreamName('apriltag')
		node.out.link(xout.input)
		self.xout = xout
	
	def build_host(self, pipeline: Pipeline, src: ImageOutStage):
		self.detector = AprilTagDetector()
		self.detector.addFamily(self.config.apriltags.tagFamily, 0)
		config = AprilTagDetector.Config()
		config.numThreads = 4
		config.refineEdges = self.config.refineEdges
		config.quadSigma = self.config.quadSigma
		config.quadDecimate = self.config.quadDecimate
		self.detector.setConfig(config)
	
	def build(self, pipeline: Pipeline, src: RgbStage | MonoStage | ImageOutStage, *args, **kwargs):
		self.field = self.config.apriltags.to_wpilib()

		if self.config.runtime == 'device':
			return self.build_device(pipeline, src)
		elif self.config.runtime == 'host':
			return self.build_host(pipeline, src)
	
	def get_params(self, device: Device, src: RgbStage | MonoStage):
		calibdata = device.readCalibration()
		at_camera = src.node
		intrinsics = calibdata.getCameraIntrinsics(src.camera_socket, destShape=(at_camera.getResolutionWidth(), at_camera.getResolutionHeight()))
		self.camera_distortion = calibdata.getDistortionCoefficients(src.camera_socket)
		fx = intrinsics[0][0]
		fy = intrinsics[1][1]
		cx = intrinsics[0][2]
		cy = intrinsics[1][2]

		estimator_cfg = AprilTagPoseEstimator.Config(
			self.config.apriltags.tagSize,
			fx, fy,
			cx, cy
		)
		self.pose_estimator = AprilTagPoseEstimator(estimator_cfg)
		self._camera_params = (fx, fy, cx, cy)

	def start_device(self, device: Device, src: RgbStage | MonoStage):
		self.get_params(device, src)
		# Poll on this stream
		return False

	def start_host(self, device: Device, src: ImageOutStage):
		self.get_params(device, src.source)
		src.add_handler(self.process_host)
		return False

	def start(self, device: Device, src: RgbStage | MonoStage | ImageOutStage, *args, **kwargs):
		if self.config.runtime == 'device':
			return self.start_device(device, src)
		elif self.config.runtime == 'host':
			return self.start_host(device, src)
	
	def handle_event(self, qname: str):
		self.events
		pass

	@property
	def events(self):
		if self.config.runtime == 'device':
			return [self.xout.getStreamName()]
		return []

	def process_device(self, packet: dai.AprilTags):
		import apriltag
		dets = list()
		def homography_compute2(c: np.ndarray):
			A = np.array([
				[c[0][0], c[0][1], 1,       0,       0, 0, -c[0][0]*c[0][2], -c[0][1]*c[0][2], c[0][2]],
				[      0,       0, 0, c[0][0], c[0][1], 1, -c[0][0]*c[0][3], -c[0][1]*c[0][3], c[0][3]],
				[c[1][0], c[1][1], 1,       0,       0, 0, -c[1][0]*c[1][2], -c[1][1]*c[1][2], c[1][2]],
				[      0,       0, 0, c[1][0], c[1][1], 1, -c[1][0]*c[1][3], -c[1][1]*c[1][3], c[1][3]],
				[c[2][0], c[2][1], 1,       0,       0, 0, -c[2][0]*c[2][2], -c[2][1]*c[2][2], c[2][2]],
				[      0,       0, 0, c[2][0], c[2][1], 1, -c[2][0]*c[2][3], -c[2][1]*c[2][3], c[2][3]],
				[c[3][0], c[3][1], 1,       0,       0, 0, -c[3][0]*c[3][2], -c[3][1]*c[3][2], c[3][2]],
				[      0,       0, 0, c[3][0], c[3][1], 1, -c[3][0]*c[3][3], -c[3][1]*c[3][3], c[3][3]],
			])
			epsilon = 1e-10
			# Eliminate.
			for col in range(8):
				# Find best row to swap with.
				# max_val = 0
				# max_val_idx = -1
				# for row in range(col, 8):
				# 	val = abs(A[row, col])
				# 	if (val > max_val):
				# 		max_val = val
				# 		max_val_idx = row
				max_val_idx = np.argmax(np.abs(A[col:,col])) + col
				max_val = np.abs(A[max_val_idx, col])

				if (max_val < epsilon):
					if self.log: self.log.warning("Matrix is singular.")
					return None

				# Swap to get best row.
				if max_val_idx != col:
					for i in range(col, 9):
						tmp = A[col, i]
						A[col, i] = A[max_val_idx, i]
						A[max_val_idx, i] = tmp

				# Do eliminate.
				for i in range(col + 1, 8):
					f = A[i, col]/A[col,col]
					A[i,col] = 0
					for j in range(col + 1, 9):
						A[i,j] -= f * A[col,j]

			# Back solve.
			for col in reversed(range(8)):
				sum = 0
				for i in range(col + 1, 8):
					sum += A[col, i] * A[i, 8]
				A[col, 8] = (A[col, 8] - sum)/A[col, col]
			return np.array([
				[A[0,9], A[1,9], A[2,9]],
				[A[3,9], A[4,9], A[5,9]],
				[A[6,9], A[7,9], 1.0],
			])
		def get_homography(det: dai.AprilTag):
			corr_arr = np.zeros((4, 4), dtype=float)
			corr_arr[(0,3),0] = -1
			corr_arr[(2,4),0] = +1
			corr_arr[(0,1),0] = -1
			corr_arr[(2,3),0] = +1

			#TODO: fix order
			corners = [det.bottomLeft, det.bottomRight, det.topLeft, det.topRight]
			for i in range(4):
				corr_arr[i,2] = corners[i].x
				corr_arr[i,3] = corners[i].y
			
			return homography_compute2(corr_arr)
		
		def homography_project(H, x: float, y: float) -> tuple[float, float]:
			xx = H[0,0] * x + H[0,1] * y + H[0,2]
			yy = H[1,0] * x + H[1,1] * y + H[1,2]
			zz = H[2,0] * x + H[2,1] * y + H[2,2]
			return (
				xx/zz,
				yy/zz
			)
		
		for tag in packet.aprilTags:
			H = get_homography(tag)
			center = homography_project(H, 0, 0)
			dets.append(apriltag.Detection(
				tag_family=self.config.apriltags.tagFamily,
				tag_id=tag.id,
				hamming=tag.hamming,
				goodness=0,
				decision_margin=tag.decisionMargin,
				homography=H,
				center=center
			))
	def process_host(self, frame: dai.ImgFrame):
		img = frame.getCvFrame()
		if len(np.shape(img)) == 3:
			img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) 
		
		dets = self.detector.detect(img)
		good_dets = list()
		for detection in dets:
			if detection.getDecisionMargin() < self.config.decisionMargin:
				continue
			if detection.getHamming() > 0:
				continue

			estimate = self.pose_estimator.estimateOrthogonalIteration(detection, self.config.numIterations)
		return self.process_dets(good_dets)


class MoeNetPipeline:
	"Pipeline builder"

	pipeline: dai.Pipeline
	stages: dict[str, PipelineStage]

	def __init__(self, config: list[ps.PipelineStageWorker], log: Optional['logging.Logger'] = None):
		self.log = log
		self.config = config
		self.stages = dict()
		self.pipeline = dai.Pipeline()
		self.providers: dict[str, Type[PipelineStage]] = {
			'slam': SlamStage,
			'mono': MonoStage,
			'rgb': RgbStage,
			'depth': DepthStage,
			'telemetry': TelemetryStage,
			'nn': ObjectDetectionStage,
			'out': ImageOutStage,
			'web': WebStreamStage,
		}
		self.labels = []
		
		self.build()
	
	@contextmanager
	def optional_stage(self, stage: S, optional: Optional[bool] = None):
		if optional is None:
			optional = stage.optional
		try:
			yield
		except:
			if optional:
				if self.log: self.log.warning("Unable to construct optional stage %s", stage.stage, exc_info=True)
			else:
				if self.log: self.log.exception("Unable to construct stage %s", stage.stage)
				raise

	def get_configs(self, ty: Type[S]) -> Iterable[S]:
		name = get_args(ty.model_fields['stage'].annotation)[0]
		for stage in self.config.root:
			if stage.stage == name and stage.enabled:
				yield stage
	
	def get_config(self, ty: Type[S], filt: Optional[Callable[[S], bool]] = None) -> Optional[S]:
		stages = self.get_configs(ty)
		if filt:
			stages = filter(filt, stages)
		stages = list(stages)

		if len(stages) == 0:
			return None

		res = stages[0]
		for stage in stages[1:]:
			if stage.optional:
				if self.log: self.log.warning("Duplicate stage %s (discarding optional)", stage.name)
				continue
			elif res.optional:
				res = stage
				if self.log: self.log.warning("Duplicate stage %s (discarding optional)", stage.name)
				continue
			else:
				# Collision
				if self.log: self.log.error("Duplicate stage %s", stage.stage)
				# Newer stage overwrites older one
				res = stage
		return res 

	def broadcast(self, cmd: AnyCmd):
		for stage in self.stages.values():
			stage.handle_command(cmd)
	
	def build(self):
		to_build = dict()
		for stage_cfg in self.config:
			to_build[stage_cfg.name] = stage_cfg
		
		def build_stage(config: S, optional: bool):
			self.log.debug("Build stage %s", config.name)
			try:
				factory = self.providers[config.stage]
				self.log.debug("Stage %s (%s) using factory %s", config.name, repr(config), factory)
				stage = factory(stage_cfg, log=self.log)
				args = list()
				for requirement, req_optional in stage.requires:
					self.log.debug("Stage %s requires %s (%s)", config.name, requirement, req_optional)
					arg = get_stage(requirement, req_optional)
					args.append(arg)
				if stage.build(self.pipeline, *args):
					# Skip stage
					return None
				self.stages[config.name] = stage
				return stage
			except:
				if optional:
					if self.log: self.log.warning("Optional stage %s failed", config.name, exc_info=True)
				else:
					if self.log: self.log.exception("Stage %s failed")
					raise

		def get_stage(name: str, optional: bool):
			if cached := self.stages.get(name, None):
				return cached
			if config := to_build.get(name, None):
				return build_stage(config, optional)

			# Infer
			fname = name.split('.')[0]
			try:
				factory = self.providers[fname]
			except KeyError:
				raise RuntimeError(f'No provider for name {fname}')
			if inferred := factory.infer(name):
				return build_stage(inferred, optional)
			if not optional:
				raise RuntimeError(f'Unable to infer config for required stage {name}')

		for stage_cfg in self.config:
			if stage_cfg.name in self.stages:
				continue
			if not stage_cfg.enabled:
				continue
			build_stage(stage_cfg, stage_cfg.optional)
		
		return self.pipeline
	
	def start(self, device: dai.Device):
		self.device = device
		self.poll_stages: list[PipelineStage] = list()
		self.events: dict[str, PipelineStage] = dict()
		started = set()
		
		def start_stage(name: str, optional: bool):
			try:
				stage = self.stages[name]
			except KeyError:
				if optional:
					return None
				else:
					raise
			
			if name in started:
				return stage
			
			args = list()
			for requirement, req_optional in stage.requires:
				arg = start_stage(requirement, req_optional)
				args.append(arg)
			if stage.start(self.device, *args) or True:
				self.poll_stages.append(stage)
			if events := stage.events:
				for event in events:
					self.events[event] = stage
				if self.log: self.log.info("Register stage %s with for events %s", stage.config.name, stage.events)

			started.add(stage)
			return stage

		for stage_name in self.stages.keys():
			if self.log: self.log.info("Start stage %s", stage_name)
			start_stage(stage_name, False)
	
	def poll(self):
		already_polled = set()
		if len(self.events) > 0:
			events = self.device.getQueueEvents(list(self.events.keys()), timeout=timedelta(seconds=0.01))
			if len(events) > 0:
				if self.log: self.log.info("Got events %s", events)
			for event in events:
				if stage := self.events.get(event, None):
					if res := stage.poll(event):
						yield from res
					already_polled.add(stage)
		
		for stage in self.poll_stages:
			if stage in already_polled:
				continue # If we processed an event, don't poll again
			if res := stage.poll(None):
				yield from res

	def close(self):
		pass