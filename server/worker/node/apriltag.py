from typing import TYPE_CHECKING, Literal, Union, Callable
from functools import cached_property

import depthai as dai
import numpy as np
import cv2

from typedef import apriltag
from typedef import pipeline as cfg
from typedef.geom import Pose3d, Translation3d, Transform3d, Rotation3d
from .builder import NodeBuilder, NodeRuntime, XOutRuntime, XLinkOut, Dependency
from ..msg import AprilTagDetection, AprilTagPose, MsgAprilTagDetections, PnpPose, PnPResult
from . import coords

if TYPE_CHECKING:
	from .video import CameraNode
	from util.timestamp import Timestamp
	from .util import ImageOutStage
	from robotpy_apriltag import AprilTagDetection as WpiAprilTagDetection, AprilTagDetector

Mat44 = np.ndarray[float, tuple[Literal[4], Literal[4]]]
Mat33 = np.ndarray[float, tuple[Literal[3], Literal[3]]]

AnyAprilTagDetection = Union['WpiAprilTagDetection', AprilTagDetection]


class AprilTagPoseList:
	def __init__(self, *poses: AprilTagPose) -> None:
		self.poses = list(poses)

	def append(self, pose: AprilTagPose):
		self.poses.append(pose)
	
	@property
	def best(self):
		return max(self.poses, key=lambda pose: pose.error)
	
	def __bool__(self):
		return len(self.poses) > 0
	def __len__(self):
		return len(self.poses)
	def __iter__(self):
		return iter(self.poses)
	def map(self, tf: Callable[[Transform3d], Transform3d]) -> 'AprilTagPoseList':
		return AprilTagPoseList(*(
			(error, tf(pose))
			for error, pose in self.poses
		))
	
	def __repr__(self):
		return repr(self.poses)

def make_object_points(knownTags: list[apriltag.AprilTagWpi], tagSize: float):
	#TODO: do this in numpy
	at_vertices = [
		Translation3d(0, -tagSize / 2.0, -tagSize / 2.0),
		Translation3d(0,  tagSize / 2.0, -tagSize / 2.0),
		Translation3d(0,  tagSize / 2.0,  tagSize / 2.0),
		Translation3d(0, -tagSize / 2.0,  tagSize / 2.0),
	]
	#TODO: especially this part
	objectTrls = [
		vtx.rotateBy(tag.pose.rotation()) + tag.pose.translation()
		for tag in knownTags
		for vtx in at_vertices
	]
	
	# Convert to OpenCV coords
	objectTrls = map(coords.wpi_to_cv2, objectTrls)
	return np.array([
		[trl.x, trl.y, trl.z]
		for trl in objectTrls
	], dtype=np.float32)

class AprilTagRuntimeBase(NodeRuntime):
	def __init__(self, config: cfg.WorkerAprilTagStageConfig, src: 'CameraNode', *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.config = config
		
		# Get camera parameters
		calibdata = self.context.device.readCalibration()
		at_camera = src.node
		self.camera_matrix = calibdata.getCameraIntrinsics(src.camera_socket, destShape=(at_camera.getResolutionWidth(), at_camera.getResolutionHeight()))
		self.camera_distortion = np.asarray(calibdata.getDistortionCoefficients(src.camera_socket))

		# Build (cached) pose estimator
		self.pose_estimator

		from robotpy_apriltag import AprilTagFieldLayout, AprilTag
		atfl_tags = list()
		for tag in self.config.apriltags.tags:
			at = AprilTag()
			at.ID = tag.ID
			at.pose = tag.pose
			atfl_tags.append(at)
		self.atfl = AprilTagFieldLayout(
			atfl_tags,
			self.config.apriltags.field.length,
			self.config.apriltags.field.width,
		)

		self.datapoints: list[AprilTagPose] = list()
	
	@cached_property
	def pose_estimator(self):
		"Estimate pose from apriltag detections"
		from robotpy_apriltag import AprilTagPoseEstimator
		fx = self.camera_matrix[0][0]
		fy = self.camera_matrix[1][1]
		cx = self.camera_matrix[0][2]
		cy = self.camera_matrix[1][2]

		estimator_cfg = AprilTagPoseEstimator.Config(
			self.config.apriltags.tagSize,
			fx, fy,
			cx, cy
		)
		self.log.info("AprilTag config %s", estimator_cfg)
		return AprilTagPoseEstimator(estimator_cfg)
	
	def _filter_detection(self, det: AnyAprilTagDetection) -> bool:
		"Check if an AprilTag detection matches the config filters"
		if det.getDecisionMargin() < self.config.decisionMargin:
			return False
		if det.getHamming() > self.config.hammingDist:
			return False
		return True
	
	def _single_pnp(self, det: AnyAprilTagDetection, fieldToTag: Pose3d | None = None):
		"Find pose from a single AprilTag detection"
		if fieldToTag is None:
			fieldToTag = self.atfl.getTagPose(det.getId())
		
		if self.config.undistort:
			corners = det.getCorners(np.empty(9, dtype=np.float32))
			corners = cv2.undistortImagePoints(corners, self.camera_matrix, self.camera_distortion)
			# Recompute homography
			H = self._homography_from_corners(corners)
			det = AprilTagDetection(
				det.getFamily(),
				det.getId(),
				det.getHamming(),
				det.getDecisionMargin(),
				corners,
				H,
			)
		
		if isinstance(det, AprilTagDetection):
			estimate = self.pose_estimator.estimateOrthogonalIteration(np.reshape(det.homography, -1), np.reshape(det.corners, -1), self.config.numIterations)
		else:
			estimate = self.pose_estimator.estimateOrthogonalIteration(det, self.config.numIterations)
		
		result: list[AprilTagPose] = []
		def append_pose(error: float, camToTag_at: Transform3d):
			# Convert camToTag coordinate system to WPI (ENU)
			camToTag_cv2 = coords.apriltag_to_cv2(camToTag_at)
			camToTag = coords.cv2_to_wpi(camToTag_cv2)

			# Compute fieldToCam if we have fieldToTag
			fieldToCam = Transform3d(Pose3d(), fieldToTag.transformBy(camToTag.inverse())) if (fieldToTag is not None) else None

			result.append(AprilTagPose(error=error, camToTag=camToTag, fieldToCam=fieldToCam))
		
		append_pose(estimate.error1, estimate.pose1)
		if np.isfinite(estimate.error2):
			append_pose(estimate.error2, estimate.pose2)
		
		return result

	def _multi_pnp(self, dets: list[AprilTagDetection]) -> PnPResult | None:
		# Find tag IDs that exist in the tag layout
		knownTags: list[apriltag.AprilTagWpi] = list()
		corners = list()
		for det in dets:
			id = det.getId()
			if pose := self.atfl.getTagPose(id):
				knownTags.append(apriltag.AprilTagWpi(ID=id, pose=pose))
				corners.append(det.corners)

		# Only run with multiple targets
		if len(knownTags) < 2:
			return None
		
		match len(knownTags):
			case 0:
				return None
			case 1:
				# Single tag PnP
				#TODO: use OpenCV here?
				det = knownTags[0]
				fieldToCam = self._single_pnp(det)
				if len(fieldToCam) == 0:
					return None
				
				return PnPResult(
					tags=set(tag.ID for tag in knownTags),
					poses=[
						PnpPose(
							error=pose.error,
							fieldToCam=pose.fieldToCam,
						)
						for pose in fieldToCam
					]
				)
			case _:
				# Multi-tag PnP
				corners = np.vstack(corners, dtype=np.float32)
				objectPoints = make_object_points(knownTags, self.config.apriltags.tagSize)

				# translate to opencv classes
				rvecs: list[np.ndarray[np.float32]] = list()
				tvecs: list[np.ndarray[np.float32]] = list()
				reprojection_error = np.zeros((1,1), np.float32)
				try:
					cv2.solvePnPGeneric(
						objectPoints,
						corners,
						self.camera_matrix,
						self.camera_distortion,
						rvecs,
						tvecs,
						False,
						cv2.SOLVEPNP_SQPNP,
						np.zeros((3, 1), np.float32), # rvec (TODO: maybe none?)
						np.zeros((3, 1), np.float32), # tvec (TODO: maybe none?)
						reprojection_error,
					)
				except:
					self.log.exception("SolvePNP_SQPNP failed")
					return None
				
				error: float = reprojection_error[0,0]
				# check if solvePnP failed with NaN results
				if np.isnan(error):
					self.log.error("SolvePNP_SQPNP NaN result")
					return None
				
				self.log.info("Got %d tvecs, %d rvecs", len(tvecs), len(rvecs))
				# Extract transform in WPI coordinates
				camToField = Transform3d(
					coords.cv2_to_wpi(Translation3d(tvecs[0][0], tvecs[0][1], tvecs[0][2])),
					coords.cv2_to_wpi(Rotation3d(rvecs[0])),
				)
				return PnPResult(
					tags=set(tag.ID for tag in knownTags),
					poses=[
						PnpPose(
							error=error,
							fieldToCam=Pose3d().transformBy(camToField.inverse()),
						)
					]
				)
	
	def _process_dets(self, ts: 'Timestamp', dets: list[Union['WpiAprilTagDetection', AprilTagDetection]]):
		if len(dets) == 0:
			self.log.debug("No AprilTags")
			return []
		
		# self.log.info("Got %s detections", len(dets))
		# for detection in dets:
		# 	if isinstance(detection, AprilTagDetection):
		# 		estimate = self.pose_estimator.estimateOrthogonalIteration(np.reshape(detection.homography, -1).tolist(), np.reshape(detection.corners, -1), self.config.numIterations)
		# 	else:
		# 		estimate = self.pose_estimator.estimateOrthogonalIteration(detection, self.config.numIterations)
		# 	self.log.info("Estimate1 %s (%s)", estimate.pose1, estimate.error1)
		# 	if np.isfinite(estimate.error2):
		# 		self.log.info("Estimate2 %s (%s)", estimate.pose2, estimate.error2)

		# Do multi-tag estimation
		multiTagsUsed: set[int] = set()
		if self.config.solvePNP and self.config.doMultiTarget:
			multiTagPose = self._multi_pnp(dets)
			if multiTagPose is None:
				self.log.info("Multi tag failed")
			else:
				self.log.info("Multi tag %s used %s", multiTagPose.poses, multiTagPose.tags)
				multiTagsUsed = multiTagPose.tags
			# for error, estimate in multiTagPose:
			# 	targetList.append(AprilTagPose(
			# 		error=error,
			# 		fieldToCamera=Pose3d().transformBy(estimate)
			# 	))
		else:
			multiTagPose = None
		
		targetList: list[AprilTagPose] = list()
		if self.config.solvePNP:
			for detection in dets:
				fieldToTag = self.atfl.getTagPose(detection.getId())
				# Do single-tag estimation when "always enabled" or if a tag was not used for multitag
				if self.config.doSingleTargetAlways or (detection.getId() not in multiTagsUsed):
					for pose in self._single_pnp(detection, fieldToTag):
						targetList.append(pose)
						self.log.debug("Single tag estimate: %s", pose.camToTag)
				elif fieldToTag is not None:
					# If single-tag estimation was not done, this is a multi-target tag from the layout
					fieldToCam = multiTagPose.best.fieldToCam if (multiTagPose is not None) else Pose3d()
					# compute this tag's camera-to-tag transform using the multitag result
					camToTag = Transform3d(fieldToCam, fieldToTag)
					# match expected AprilTag coordinate system
					# camToTag_cv2 = coords.wpi_to_cv2(camToTag_wpi)
					# camToTag_at = coords.cv2_to_apriltag(camToTag_cv2)
					# tagPoseEstimate = AprilTagPoseList((0, camToTag_at))
					targetList.append(AprilTagPose(
						error=0,
						camToTag=camToTag,
						fieldToCam=fieldToCam,
					))
		# for v in targetList:
		# 	self.datapoints.append(v)

		yield MsgAprilTagDetections(
			timestamp=ts.nanos,
			poses=targetList,
			pnp=multiTagPose,
		)
		if len(self.datapoints) > 300:
			from matplotlib import pyplot as plt
			errors = np.zeros(len(self.datapoints))
			tfs = np.zeros((len(self.datapoints), 6))
			for i, v in enumerate(self.datapoints):
				errors[i] = v.error
				tf = v.camToTag
				tfs[i, :] = (tf.translation().x, tf.translation().y, tf.translation().z, tf.rotation().x, tf.rotation().y, tf.rotation().z)
			
			tf_avg = np.average(tfs, axis=0)
			tfs -= tf_avg
			plt.xlabel('error')
			for i, l in enumerate('xyzpry'):
				plt.scatter(errors, np.abs(tfs[:, i]), label=l)
			plt.legend()
			plt.show()
			self.datapoints.clear()
		# self.log.warning("Targets: %s", targetList)
			
	
	@staticmethod
	def _homography_project(H: Mat33, x: float, y: float) -> tuple[float, float]:
		xx = H[0,0] * x + H[0,1] * y + H[0,2]
		yy = H[1,0] * x + H[1,1] * y + H[1,2]
		zz = H[2,0] * x + H[2,1] * y + H[2,2]
		return (
			xx/zz,
			yy/zz
		)
	
	def _homography_from_corners(self, corners: Union[tuple[dai.Point2f, ...], np.ndarray[float, tuple[Literal[4], Literal[2]]]]):
		"Reconstruct homography matrix from corners"
		corr_arr = np.zeros((4, 4), dtype=np.float32)
		corr_arr[(0,3),0] = -1
		corr_arr[(0,1),1] = -1
		corr_arr[(1,2),0] = +1
		corr_arr[(2,3),1] = +1

		#TODO: fix order
		if hasattr(corners[0], 'x'):
			for i in range(4):
				corr_arr[i,2] = corners[i].x
				corr_arr[i,3] = corners[i].y
		else:
			corr_arr[:,(2,3)] = corners[:]
		
		return self._homography_compute2(corr_arr)
	
	def _homography_compute2(self, c: Mat44) -> Mat33:
		A = np.zeros((8,9), dtype=float)
		# Even rows (start at 0)
		A[::2,(0,1)] = c[:,(0,1)]
		A[::2,2] = 1
		A[::2,6] = -c[:,0] * c[:,2]
		A[::2,7] = -c[:,1] * c[:,2]
		A[::2,8] = c[:,2]
		# Odd rows
		A[1::2,(3,4)] = c[:,(0,1)]
		A[1::2,5] = 1
		A[1::2,6] = -c[:,0]*c[:,3]
		A[1::2,7] = -c[:,1]*c[:,3]
		A[1::2,8] = c[:,3]
		# A = np.array([
		# 	[c[0,0], c[0,1], 1,      0,      0, 0, -c[0,0]*c[0,2], -c[0,1]*c[0,2], c[0,2]],
		# 	[     0,      0, 0, c[0,0], c[0,1], 1, -c[0,0]*c[0,3], -c[0,1]*c[0,3], c[0,3]],
		# 	[c[1,0], c[1,1], 1,      0,      0, 0, -c[1,0]*c[1,2], -c[1,1]*c[1,2], c[1,2]],
		# 	[     0,      0, 0, c[1,0], c[1,1], 1, -c[1,0]*c[1,3], -c[1,1]*c[1,3], c[1,3]],
		# 	[c[2,0], c[2,1], 1,      0,      0, 0, -c[2,0]*c[2,2], -c[2,1]*c[2,2], c[2,2]],
		# 	[     0,      0, 0, c[2,0], c[2,1], 1, -c[2,0]*c[2,3], -c[2,1]*c[2,3], c[2,3]],
		# 	[c[3,0], c[3,1], 1,      0,      0, 0, -c[3,0]*c[3,2], -c[3,1]*c[3,2], c[3,2]],
		# 	[     0,      0, 0, c[3,0], c[3,1], 1, -c[3,0]*c[3,3], -c[3,1]*c[3,3], c[3,3]],

		# 	[c[0,0], c[0,1], 1,      0,      0, 0, -c[0,0]*c[0,2], -c[0,1]*c[0,2], c[0,2]],
		# 	[c[1,0], c[1,1], 1,      0,      0, 0, -c[1,0]*c[1,2], -c[1,1]*c[1,2], c[1,2]],
		# 	[c[2,0], c[2,1], 1,      0,      0, 0, -c[2,0]*c[2,2], -c[2,1]*c[2,2], c[2,2]],
		# 	[c[3,0], c[3,1], 1,      0,      0, 0, -c[3,0]*c[3,2], -c[3,1]*c[3,2], c[3,2]],
		# 	[     0,      0, 0, c[0,0], c[0,1], 1, -c[0,0]*c[0,3], -c[0,1]*c[0,3], c[0,3]],
		# 	[     0,      0, 0, c[1,0], c[1,1], 1, -c[1,0]*c[1,3], -c[1,1]*c[1,3], c[1,3]],
		# 	[     0,      0, 0, c[2,0], c[2,1], 1, -c[2,0]*c[2,3], -c[2,1]*c[2,3], c[2,3]],
		# 	[     0,      0, 0, c[3,0], c[3,1], 1, -c[3,0]*c[3,3], -c[3,1]*c[3,3], c[3,3]],
		# ])
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
				A[(col, max_val_idx), col:] = A[(max_val_idx, col), col:]
			
			# Do eliminate.
			# f = A[col+1:,col]/A[col,col]
			for i in range(col + 1, 8):
				f = A[i, col]/A[col,col]
				A[i,col] = 0
				A[i,col+1:] -= f * A[col,col+1:]

		# Back solve.
		for col in reversed(range(8)):
			sum = np.sum(A[col, col+1:-1] * A[col+1:, 8])
			A[col, 8] = (A[col, 8] - sum)/A[col, col]
		# Not sure why I have to flip the second column, but it makes it work
		return np.array([
			[A[0,8], -A[1,8], A[2,8]],
			[A[3,8], -A[4,8], A[5,8]],
			[A[6,8], -A[7,8], 1.0],
		])

class AprilTagHostRuntime(AprilTagRuntimeBase):
	do_poll = False

	def __init__(self, src_out: 'ImageOutStage', *args, **kwargs) -> None:
		super().__init__(*args, src=src_out.source, **kwargs)

		from robotpy_apriltag import AprilTagDetector
		
		self.detector = AprilTagDetector()
		# We could, theoretically, support multiple families
		self.detector.addFamily(self.config.apriltags.tagFamily, self.config.hammingDist)
		det_cfg = self._detector_config()
		self.detector.setConfig(det_cfg)
		src_out.add_handler(self._process_host)
	
	def _detector_config(self) -> 'AprilTagDetector.Config':
		"Compute AprilTag detector config"
		# In the future it'd be great to allow changes without restarting the whole process
		from robotpy_apriltag import AprilTagDetector
		det_cfg = AprilTagDetector.Config()
		if self.config.detectorThreads is not None:
			det_cfg.numThreads = self.config.detectorThreads
		else:
			det_cfg.numThreads = 4
		det_cfg.refineEdges = self.config.refineEdges
		det_cfg.quadSigma = self.config.quadSigma
		det_cfg.quadDecimate = self.config.quadDecimate
		det_cfg.refineEdges = self.config.refineEdges
		if self.config.decodeSharpening is not None:
			det_cfg.decodeSharpening = self.config.decodeSharpening
		return det_cfg
	
	def _check_homography(self, detection: 'WpiAprilTagDetection'):
		# Re-compute homography
		corners = [
			detection.getCorner(i)
			for i in range(4)
		]
		H = self._homography_from_corners(corners)
		c = self._homography_project(H, 0, 0)
		EPS = 1e-10
		if not np.all((H - detection.getHomographyMatrix()) < EPS):
			self.log.error("Compare real %s to computed %s", detection.getHomographyMatrix(), H)
		if not np.all((c - np.array([detection.getCenter().x, detection.getCenter().y])) < EPS):
			self.log.error("Bad center")
	
	def _process_host(self, frame: dai.ImgFrame):
		"Process a frame"
		ts = self.context.local_timestamp(frame)
		img = frame.getCvFrame()
		# Always convert to BGR (TODO: maybe use ImageManip?)
		if len(np.shape(img)) == 3:
			img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) 
		
		dets = self.detector.detect(img)
		self.log.debug("raw ats %s", dets)
		good_dets = list()
		for detection in dets:
			if not self._filter_detection(detection):
				continue

			# self._check_homography(detection)

			if True:
				# center = detection.getCenter()
				detection = AprilTagDetection(
					tag_family=detection.getFamily(),
					tag_id=detection.getId(),
					hamming=detection.getHamming(),
					decision_margin=detection.getDecisionMargin(),
					homography=detection.getHomographyMatrix(),
					corners=np.reshape(np.asarray(detection.getCorners([0] * 8)), (4, 2)),
					# center=np.array([center.x, center.y], dtype=float),
				)
			good_dets.append(detection)
			
		return self._process_dets(ts, good_dets)

class AprilTagDeviceRuntime(XOutRuntime[dai.AprilTags], AprilTagRuntimeBase):
	def __init__(self, context: NodeRuntime.Context, config: cfg.WorkerAprilTagStageConfig, src: 'CameraNode', xout: XLinkOut[dai.AprilTags]) -> None:
		super().__init__(context=context, config=config, src=src, xout=xout)
	
	def _get_homography(self, det: dai.AprilTag):
		corners = [det.bottomLeft, det.bottomRight, det.topLeft, det.topRight]
		return self._homography_from_corners(corners)
	
	def handle(self, packet: dai.AprilTags):
		ts = self.context.local_timestamp(packet)
		dets = list()
		
		for tag in packet.aprilTags:
			corners = np.empty((4,2), dtype=np.float32)
			for i, corner in enumerate([tag.bottomLeft, tag.bottomRight, tag.topLeft, tag.topRight]):
				corners[i,0] = corner.x
				corners[i,1] = corner.y
			
			H = self._homography_from_corners(corners)
			if H is None:
				continue
			
			# center = self._homography_project(H, 0, 0)
			dets.append(AprilTagDetection(
				tag_family=self.config.apriltags.tagFamily,
				tag_id=tag.id,
				hamming=tag.hamming,
				decision_margin=tag.decisionMargin,
				homography=H,
				corners=corners,
				# center=center
			))
		self.log.info("Got raw dets %s", dets)
		return self._process_dets(ts, dets)

def map_family(family: str | apriltag.AprilTagFamily) -> dai.AprilTagConfig.Family:
	match family:
		case 'tag16h5' | apriltag.AprilTagFamily.TAG_16H5:
			return dai.AprilTagConfig.Family.TAG_16H5
		case 'tag25h9' | apriltag.AprilTagFamily.TAG_25H9:
			return dai.AprilTagConfig.Family.TAG_25H9
		case 'tag36h10' | apriltag.AprilTagFamily.TAG_36H10:
			return dai.AprilTagConfig.Family.TAG_36H10
		case 'tag36h11' | apriltag.AprilTagFamily.TAG_36H11:
			return dai.AprilTagConfig.Family.TAG_36H11
		case 'tagCircle21h7' | apriltag.AprilTagFamily.TAG_CIR21H7:
			return dai.AprilTagConfig.Family.TAG_CIR21H7
		case 'tagStandard41h12' | apriltag.AprilTagFamily.TAG_STAND41H12:
			return dai.AprilTagConfig.Family.TAG_STAND41H12
		case _:
			raise ValueError(f'Unknown AprilTag family {family}')

class AprilTagBuilder(NodeBuilder[cfg.WorkerAprilTagStageConfig]):
	@property
	def requires(self):
		match self.config.runtime:
			case 'host':
				return [Dependency(f'xout.{self.config.camera}')]
			case 'device':
				match self.config.camera:
					case 'rgb':
						return [Dependency('rgb')]
					case 'left':
						return [Dependency('mono.left')]
					case 'right':
						return [Dependency('mono.right')]
	
	def build_device(self, pipeline: dai.Pipeline, src: 'CameraNode'):
		apriltag = pipeline.createAprilTag()

		atConfig = apriltag.initialConfig.get()
		tag_family = map_family(self.config.apriltags.tagFamily)
		self.log.debug("AprilTag using family %s", tag_family)
		atConfig.family = tag_family
		atConfig.quadDecimate = self.config.quadDecimate
		atConfig.quadSigma = self.config.quadSigma
		atConfig.refineEdges = self.config.refineEdges
		if (hammingDist := self.config.hammingDist) is not None:
			atConfig.maxHammingDistance = hammingDist
		apriltag.initialConfig.set(atConfig)

		apriltag.inputImage.setBlocking(False)
		apriltag.inputImage.setQueueSize(1)

		if self.config.camera == 'rgb':
			manip = pipeline.createImageManip()
			manip.initialConfig.setResize(480, 270)
			manip.initialConfig.setFrameType(dai.ImgFrame.Type.GRAY8)

			src.video_out.link(manip.inputImage)
			manip.out.link(apriltag.inputImage)
		else:
			src.video_out.link(apriltag.inputImage)

		xout = pipeline.createXLinkOut()
		xout.setStreamName('apriltag')
		apriltag.out.link(xout.input)

		self.xout = xout
	
	def build_host(self, pipeline: dai.Pipeline, src: 'ImageOutStage'):
		return
	
	def build(self, pipeline: dai.Pipeline, src: Union['CameraNode', 'ImageOutStage'], *args, **kwargs):
		self.field = self.config.apriltags.to_wpilib()

		if self.config.runtime == 'device':
			return self.build_device(pipeline, src)
		elif self.config.runtime == 'host':
			return self.build_host(pipeline, src)

	def start(self, context: NodeRuntime.Context, src: Union['CameraNode', 'ImageOutStage'], *args, **kwargs):
		match self.config.runtime:
			case 'device':
				return AprilTagDeviceRuntime(
					src=src,
					context=context,
					config=self.config,
					xout=self.xout,
				)
			case 'host':
				src: ImageOutStage
				return AprilTagHostRuntime(
					src_out=src,
					context=context,
					config=self.config,
				)
	