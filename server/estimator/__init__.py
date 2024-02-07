from typing import Optional, overload
import logging
from collections import OrderedDict

from wpiutil.log import DataLog, DoubleLogEntry

from worker.msg import MsgPose, MsgDetections, MsgAprilTagPoses
from wpi_compat.datalog import StructLogEntry, StructArrayLogEntry, ProtoLogEntry
from typedef.geom import Transform3d, Rotation3d, Pose3d
from typedef import net, cfg
from util.log import child_logger
from util.clock import Clock, WallClock
from util.timemap import TimeMapper, IdentityTimeMapper
from util.timestamp import Timestamp

from .estimator import PoseEstimator
from .tracker import ObjectTracker


class DataFusion:
	pose_estimator: PoseEstimator
	object_tracker: ObjectTracker

	def __init__(self, config: cfg.EstimatorConfig, clock: Optional[Clock] = None, *, log: Optional[logging.Logger], datalog: Optional[DataLog] = None) -> None:
		self.log = child_logger("data", log)
		self.datalog = datalog
		self.clock = clock or WallClock()
		self.config = config

		self.pose_estimator = PoseEstimator(config.pose, self.clock, log=self.log, datalog=self.datalog)
		self.object_tracker = ObjectTracker(config.detections)

		# Datalogs
		if self.datalog is not None:
			self.log_f2r = StructLogEntry(self.datalog, 'filt/fieldToRobot', Pose3d)
			self.log_f2o = StructLogEntry(self.datalog, 'filt/fieldToOdom', Pose3d)
			self.log_o2r = StructLogEntry(self.datalog, 'filt/odomToRobot', Transform3d)
			self.log_objdet = StructArrayLogEntry(self.datalog, 'filt/fieldToDetections', Pose3d)
			self.log_objdet_full = ProtoLogEntry(self.datalog, 'filt/detections', net.ObjectDetections)
			self.logFpsF2R = DoubleLogEntry(datalog, 'fps/field_to_robot')
			self.logFpsF2O = DoubleLogEntry(datalog, 'fps/field_to_odom')
			self.logFpsApriltag = DoubleLogEntry(datalog, 'fps/apriltag')
			self.logFpsDetections = DoubleLogEntry(datalog, 'fps/detections')
			now = clock.now()
			self._last_f2r_ts = now
			self._last_f2o_ts = now
			self._last_apr_ts = now
			self._last_det_ts = now

		# Track fresh data
		self.fresh_f2r = True
		self.fresh_f2o = True
		self.fresh_o2r = True
		self.fresh_det = True
	
	def record_f2r(self, robot_to_camera: Transform3d, msg: MsgPose):
		timestamp = Timestamp.from_nanos(msg.timestamp, WallClock())
		self.pose_estimator.record_f2r(robot_to_camera, msg)

		if self.datalog is not None:
			simple_f2o = msg.pose.transformBy(robot_to_camera.inverse())
			self.log_f2o.append(simple_f2o)
			
			delta = timestamp - self._last_f2r_ts
			self._last_f2r_ts = timestamp
			self.logFpsF2R.append(1.0 / delta.total_seconds())
		
		self.fresh_f2r = True
		self.fresh_o2r = True
	
	def record_f2o(self, timestamp: Timestamp, field_to_odom: Pose3d):
		if self.datalog:
			delta = timestamp - self._last_f2o_ts
			self._last_f2o_ts = timestamp
			self.logFpsF2O.append(1.0 / delta.total_seconds())
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
		res: list[net.ObjectDetection] = list()
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
	
	def record_apriltag(self, robot_to_camera: Transform3d, apriltags: MsgAprilTagPoses):
		timestamp = Timestamp.from_nanos(apriltags.timestamp, clock=WallClock())
		if self.datalog:
			delta = timestamp - self._last_apr_ts
			self._last_apr_ts = timestamp
			self.logFpsApriltag.append(1.0 / delta.total_seconds())
		
		self.fresh_f2r = True
		self.pose_estimator.record_apriltag(timestamp, robot_to_camera, apriltags.poses)
	
	def record_detections(self, robot_to_camera: Transform3d, detections: MsgDetections, mapper_loc: Optional[TimeMapper] = None):
		"Record some detections for tracking"
		if mapper_loc is not None:
			assert mapper_loc.clock_b == self.clock
		
		# I'm not super happy with this method being on PoseEstimator, but whatever
		timestamp     = Timestamp.from_nanos(detections.timestamp)
		timestamp_loc = timestamp if (mapper_loc is None) else mapper_loc.a_to_b(timestamp)

		if self.datalog:
			delta = timestamp - self._last_det_ts
			self._last_det_ts = timestamp
			self.logFpsDetections.append(1.0 / delta.total_seconds())

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
		res: list[net.ObjectDetection] = list()

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