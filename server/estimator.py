from typing import List, Optional, TYPE_CHECKING, Dict, overload
from collections import OrderedDict
import logging

import numpy as np
from wpimath.interpolation._interpolation import TimeInterpolatablePose3dBuffer
from wpiutil.log import DataLog

from typedef.worker import MsgPose, MsgDetections
from typedef.cfg import EstimatorConfig
from nt_util.log import StructLogEntry, StructArrayLogEntry, ProtoLogEntry
from typedef.geom import Transform3d, Translation3d, Rotation3d, Pose3d
from typedef import net
from util.clock import Clock, WallClock
from util.timemap import TimeMapper, IdentityTimeMapper
from util.timestamp import Timestamp


def interpolate_pose3d(a: Pose3d, b: Pose3d, t: float) -> Pose3d:
	"Interpolate between `Pose3d`s"
	if t <= 0:
		return a
	if t >= 1:
		return b
	twist = a.log(b)
	return a.exp(twist * t)


class TrackedObject:
	def __init__(self, id: int, timestamp: Timestamp, position: Translation3d, label: str, confidence: float):
		self.id = id
		"Tracking ID"
		self.position = position
		"Estimated object position"
		self.label = label
		"Detection label"
		self.last_seen = timestamp
		self.n_detections = 1
		self.confidence = confidence
		"Detection confidence"
		self._position_rs_cache = None

	def update(self, other: 'TrackedObject', alpha: float = 0.2):
		self.last_seen = other.last_seen

		# LERP (TODO: use confidence?)
		self.position = (other.position * alpha) + (self.position * (1.0 - alpha))
		self.n_detections += 1
	
	@property
	def pose(self):
		"Get position as Pose3d"
		return Pose3d(self.position, Rotation3d())
	
	def position_rel(self, reference_pose: Pose3d) -> Translation3d:
		"Get position relative to some reference"
		# Cache position_rs, as we'll probably compute the same transforms a lot
		if (self._position_rs_cache is None) or (self._position_rs_cache[0] != reference_pose):
			position_rs = self.pose.relativeTo(reference_pose).translation()
			self._position_rs_cache = (reference_pose, position_rs)
		
		return self._position_rs_cache[1]
	
	def should_remove(self, now: Timestamp, config: EstimatorConfig):
		if self.n_detections < config.object_min_detections and self.last_seen < now - config.object_detected_duration:
			return True
		if self.last_seen < now - config.object_history_duration:
			return True
		return False

	def __str__(self):
		return f'{self.label}@{self.id}'


class ObjectTracker:
	tracked_objects: Dict[str, List[TrackedObject]]

	def __init__(self, config: EstimatorConfig) -> None:
		self.tracked_objects = dict()
		self._next_id = 0
		self.config = config

	def _find_best_match(self, new_obj: TrackedObject, field_to_camera: Pose3d):
		new_cs = new_obj.position_rel(field_to_camera)

		best = None
		best_dist = self.config.object_clustering_distance
		for old in self.tracked_objects.setdefault(new_obj.label, []):
			# ignore depth difference in clustering
			old_cs = new_obj.position_rel(field_to_camera)

			# Distance away from camera
			z = max(self.config.object_min_depth, old_cs.z, new_cs.z)
			dist: float = np.hypot(old_cs.x - new_cs.x, old_cs.y - new_cs.y) / z

			if dist < best_dist:
				best_dist = dist
				best = old
		# if best: print(f'matched with {best} (seen {best.n_detections} time(s))')
		return best

	def track(self, t: Timestamp, detections: MsgDetections, field_to_robot: Pose3d, robot_to_camera: Transform3d):
		"Track some objects"
		field_to_camera = field_to_robot + robot_to_camera

		for detection in detections:
			cam_to_obj = Translation3d(
				x=detection.position.x,
				y=-detection.position.y, # Flipped y (it was in the SAI example)
				z=detection.position.z,
			)
			field_to_obj = (field_to_camera + Transform3d(cam_to_obj, Rotation3d())).translation()
			label = detection.label

			id = self._next_id
			new_obj = TrackedObject(id, t, field_to_obj, label, confidence=detection.confidence)
			if existing := self._find_best_match(new_obj, field_to_camera):
				existing.update(new_obj, alpha=self.config.object_alpha)
			else:
				self._next_id += 1 # Only bump IDs for new objects
				self.tracked_objects.setdefault(label, []) \
					.append(new_obj)
		
		self.cleanup(t)
	
	def cleanup(self, t: Timestamp):
		# remove cruft
		tracked_objects: Dict[str, List[TrackedObject]] = dict()
		for key, value in self.tracked_objects.items():
			value1 = [
				obj
				for obj in value
				if not obj.should_remove(t, self.config)
			]
			if len(value1) > 0:
				tracked_objects[key] = value1
		self.tracked_objects = tracked_objects
	
	def items(self):
		return (
			o
			for l in self.tracked_objects.values()
			for o in l
			if o.n_detections >= self.config.object_min_detections
		)

	def clear(self):
		self.tracked_objects.clear()


class PoseEstimator:
	"""
	We need to merge together (often) conflicting views of the world.
	"""
	def __init__(self, config: EstimatorConfig, clock: Clock, *, log: logging.Logger, datalog: Optional[DataLog] = None) -> None:
		self.log = log.getChild('pose')
		self.datalog = datalog
		self.config = config

		if self.datalog is not None:
			self.logFieldToRobot = StructLogEntry(datalog, 'raw/fieldToRobot', Pose3d)
			self.logFieldToOdom = StructLogEntry(datalog, 'raw/fieldToOdom', Pose3d)

		self.clock = clock
		self._last_o2r = Transform3d()
		"Last `odom`→`robot` (for caching `odom_to_robot()`)"

		pose_history = config.pose_history.total_seconds()
		if pose_history < 0:
			self.log.error("Negative pose history (%s). Default to zero.", config.pose_history)
			pose_history = 0
		elif pose_history == 0:
			self.log.warning("No pose history (syncing f2r and f2o may not work right)")

		self.buf_field_to_robot = TimeInterpolatablePose3dBuffer(config.pose_history.total_seconds(), interpolate_pose3d)
		"Buffer for `field`→`robot` transforms (for sync with odometry)"
		self.buf_field_to_odom = TimeInterpolatablePose3dBuffer(config.pose_history.total_seconds(), interpolate_pose3d)
		"Buffer for `field`→`odom` transforms (for sync with absolute pose)"
	
	def odom_to_robot(self) -> Transform3d:
		"Get the best estimated `odom`→`robot` corrective transform"
		samples_f2o = self.buf_field_to_odom.getInternalBuffer()
		samples_f2r = self.buf_field_to_robot.getInternalBuffer()

		# Return identity if we don't have any data
		if (len(samples_f2o) == 0) or (len(samples_f2r) == 0):
			self.log.debug("No data to compute odom→robot correction")
			return self._last_o2r
		
		# Find timestamps of overlapping range between field→odom and field→robot data
		first_f2o = samples_f2o[0][0]
		first_f2r = samples_f2r[0][0]
		ts_start = max(first_f2o, first_f2r)

		last_f2o = samples_f2o[-1][0]
		last_f2r = samples_f2r[-1][0]
		ts_end = min(last_f2o, last_f2r)
		if ts_end < ts_start:
			# No overlap
			self.log.debug("No overlap between field→odom and field→robot data")
			return self._last_o2r
		
		# We want the most recent pair that overlap
		f2o = self.buf_field_to_odom.sample(ts_end)
		assert f2o is not None
		f2r = self.buf_field_to_robot.sample(ts_end)
		assert f2r is not None
		
		res = Transform3d(f2o, f2r)
		self._last_o2r = res
		return res
	
	def field_to_robot(self, time: Timestamp) -> Pose3d:
		"Get the `field`→`robot` transform at a specified time"
		if res := self.buf_field_to_robot.sample(time.as_seconds()):
			return res
		# Return zero if we don't have any info
		return Pose3d()
	
	def field_to_odom(self, time: Timestamp) -> Pose3d:
		"Get the `field`→`odom` transform at a specified time"
		if res := self.buf_field_to_odom.sample(time.as_seconds()):
			return res
		# Return zero if we don't have any info
		return Pose3d()
	
	def record_f2r(self, robot_to_camera: Transform3d, msg: MsgPose):
		"Record SLAM pose"
		field_to_camera = msg.pose
		field_to_robot = field_to_camera.transformBy(robot_to_camera.inverse())
		timestamp = Timestamp.from_nanos(msg.timestamp)

		if self.datalog is not None:
			self.logFieldToRobot.append(field_to_robot, timestamp.as_wpi())
		
		self.buf_field_to_robot.addSample(timestamp.as_seconds(), field_to_robot)
	
	def record_f2o(self, timestamp: Timestamp, field_to_odom: Pose3d):
		"Record odometry pose"
		if self.datalog is not None:
			self.logFieldToOdom.append(field_to_odom, timestamp.as_wpi())
		
		self.buf_field_to_odom.addSample(timestamp.as_seconds(), field_to_odom)
	
	def clear(self):
		self.buf_field_to_odom.clear()
		self.buf_field_to_robot.clear()
		self._last_o2r = Transform3d()


class DataFusion:
	pose_estimator: PoseEstimator
	object_tracker: ObjectTracker

	def __init__(self, config: EstimatorConfig, clock: Optional[Clock] = None, *, log: Optional[logging.Logger], datalog: Optional[DataLog] = None) -> None:
		self.log = logging.getLogger("data") if log is None else log.getChild("data")
		self.datalog = datalog
		self.clock = clock or WallClock()
		self.config = config

		self.pose_estimator = PoseEstimator(config, self.clock, log=self.log, datalog=self.datalog)
		self.object_tracker = ObjectTracker(config)

		# Datalogs
		if self.datalog is not None:
			self.log_f2r = StructLogEntry(self.datalog, 'filt/fieldToRobot', Pose3d)
			self.log_f2o = StructLogEntry(self.datalog, 'filt/fieldToOdom', Pose3d)
			self.log_o2r = StructLogEntry(self.datalog, 'filt/odomToRobot', Transform3d)
			self.log_objdet = StructArrayLogEntry(self.datalog, 'filt/fieldToDetections', Pose3d)
			self.log_objdet_full = ProtoLogEntry(self.datalog, 'filt/detections', net.ObjectDetections)

		# Track fresh data
		self.fresh_f2r = True
		self.fresh_f2o = True
		self.fresh_o2r = True
		self.fresh_det = True
	
	def record_f2r(self, robot_to_camera: Transform3d, msg: MsgPose):
		self.pose_estimator.record_f2r(robot_to_camera, msg)
		if self.datalog is not None:
			simple_f2o = msg.pose.transformBy(robot_to_camera.inverse())
			self.log_f2o.append(simple_f2o)
		self.fresh_f2r = True
		self.fresh_o2r = True
	
	def record_f2o(self, timestamp: Timestamp, field_to_odom: Pose3d):
		self.pose_estimator.record_f2o(timestamp, field_to_odom)
		self.fresh_f2o = True
		self.fresh_o2r = True
	
	@overload
	def odom_to_robot(self) -> Transform3d: ...
	def odom_to_robot(self, fresh: bool = False) -> Optional[Transform3d]:
		"Get the best estimated `odom`→`robot` corrective transform"
		if fresh and (not self.fresh_o2r):
			return None
		res = self.pose_estimator.odom_to_robot()
		if fresh:
			self.fresh_o2r = False
			if self.datalog is not None:
				self.log_o2r.append(res)
		return res
	
	@overload
	def field_to_robot(self) -> Pose3d: ...
	def field_to_robot(self, fresh: bool = False) -> Optional[Pose3d]:
		"Get the most recent `field`→`robot` transform"
		if fresh and (not self.fresh_f2r):
			return None
		ts = self.clock.now()
		res = self.pose_estimator.field_to_robot(ts)
		if fresh:
			self.fresh_f2r = False
			if self.datalog is not None:
				self.log_f2r.append(res)
		return res
	
	def transform_detections(self, robot_to_camera: Transform3d, detections: MsgDetections, mapper_loc: Optional[TimeMapper] = None, mapper_net: Optional[TimeMapper] = None) -> net.ObjectDetections:
		"Transform detections message into robot-space"
		if mapper_loc is not None:
			assert mapper_loc.clock_b == self.clock
		if mapper_net is not None:
			assert mapper_net.clock_a == self.clock
		
		# I'm not super happy with this method being on PoseEstimator, but whatever
		labels: OrderedDict[str, int] = OrderedDict()
		res: List[net.ObjectDetection] = list()
		timestamp     = detections.timestamp
		timestamp_loc = timestamp     if (mapper_loc is None) else mapper_loc.a_to_b(timestamp)
		timestamp_net = timestamp_loc if (mapper_net is None) else mapper_net.a_to_b(timestamp_loc)
		timestamp_net = net.Timestamp(
			seconds=int(timestamp_net / 1e9),
			nanos=int(timestamp_net % 1e9),
		)

		field_to_robot = Transform3d(Pose3d(), self.pose_estimator.field_to_robot(Timestamp.from_nanos(timestamp_loc)))
		field_to_camera = field_to_robot + robot_to_camera

		for detection in detections.detections:
			# Lookup or get next ID
			label_id = labels.setdefault(detection.label, len(labels))

			# Compute transforms
			camera_to_object = Transform3d(detection.position, Rotation3d())
			positionRobot = robot_to_camera + camera_to_object
			positionField = field_to_camera + camera_to_object

			# Fix datatype (ugh)
			detection_net = net.ObjectDetection(
				timestamp=timestamp_net,
				label_id=label_id,
				confidence=detection.confidence,
				positionRobot=net.Translation3d(
					x=positionRobot.x,
					y=positionRobot.y,
					z=positionRobot.z,
				),
				positionField=net.Translation3d(
					x=positionField.x,
					y=positionField.y,
					z=positionField.z,
				),
			)
			res.append(detection_net)
		
		return net.ObjectDetections(
			labels=list(labels.keys()),
			detections=res,
		)
	
	def record_detections(self, robot_to_camera: Transform3d, detections: MsgDetections, mapper_loc: Optional[TimeMapper] = None):
		"Record some detections for tracking"
		if mapper_loc is not None:
			assert mapper_loc.clock_b == self.clock
		
		# I'm not super happy with this method being on PoseEstimator, but whatever
		timestamp     = Timestamp.from_nanos(detections.timestamp)
		timestamp_loc = timestamp if (mapper_loc is None) else mapper_loc.a_to_b(timestamp)

		field_to_robot = self.pose_estimator.field_to_robot(timestamp_loc)

		self.object_tracker.track(timestamp, detections, field_to_robot, robot_to_camera)
		self.fresh_det = True

	def get_detections(self, mapper_net: Optional[TimeMapper] = None, *, fresh = False) -> Optional[net.ObjectDetections]:
		"Get any new detections"
		if fresh and (not self.fresh_det):
			return None
		
		if mapper_net is None:
			mapper_net = IdentityTimeMapper(self.clock)
		assert mapper_net.clock_a == self.clock

		labels: OrderedDict[str, int] = OrderedDict()
		res: List[net.ObjectDetection] = list()

		for detection in self.object_tracker.items():
			# Lookup or get next ID
			label_id = labels.setdefault(detection.label, len(labels))

			ts_loc = detection.last_seen
			s, ns = mapper_net.a_to_b(ts_loc).split()
			ts_net = net.Timestamp(seconds=s, nanos=ns)

			# Compute transforms
			field_to_robot = self.pose_estimator.field_to_robot(ts_loc)
			field_to_object = detection.position
			robot_to_object = detection.position_rel(field_to_robot)

			# Fix datatype (ugh)
			res.append(net.ObjectDetection(
				timestamp=ts_net,
				label_id=label_id,
				confidence=detection.confidence,
				positionRobot=net.Translation3d(
					x=robot_to_object.x,
					y=robot_to_object.y,
					z=robot_to_object.z,
				),
				positionField=net.Translation3d(
					x=field_to_object.x,
					y=field_to_object.y,
					z=field_to_object.z,
				),
			))
		if fresh:
			self.fresh_det = False
		
		res = net.ObjectDetections(
			labels=list(labels.keys()),
			detections=res,
		)
		if self.datalog is not None:
			self.log_objdet_full.append(res)
			poses = [det.pose for det in self.object_tracker.items()]
			self.log_objdet.append(poses)
		return res