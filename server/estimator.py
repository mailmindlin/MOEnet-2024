from typing import List, Optional, TYPE_CHECKING, Dict
from collections import OrderedDict
import logging

import numpy as np
from wpimath.geometry import Transform3d, Translation3d, Rotation3d, Pose3d
from wpimath.interpolation._interpolation import TimeInterpolatablePose3dBuffer
from wpimath.units import seconds
from wpiutil.log import DataLog

from .typedef.worker import MsgPose, MsgDetections
from .typedef.cfg import EstimatorConfig
from .nt_util.log import StructLogEntry
from .typedef.geom import Pose3d, Transform3d
from .typedef import net
from .clock import Clock, MonoClock, TimeMapper, Timestamp


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
        self.position = position
        self.label = label
        self.last_seen = timestamp
        self.n_detections = 1
        self.confidence = confidence
        self._position_rs_cache = None

    def update(self, other: 'TrackedObject', alpha: float = 0.2):
        self.last_seen = other.last_seen

        # LERP (TODO: use confidence?)
        self.position = (other.position * alpha) + (self.position * (1.0 - alpha))
        self.n_detections += 1
    
    @property
    def pose(self):
        return Pose3d(self.position, Rotation3d())
    
    def position_rel(self, reference_pose: Pose3d) -> Translation3d:
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
        # w_to_c_mat = np.linalg.inv(view_mat)
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
            new_obj = TrackedObject(id, t, field_to_obj, label)
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
            self.logFieldToRobot = StructLogEntry(datalog, '/pose/fieldToRobot', Pose3d)
            self.logFieldToOdom = StructLogEntry(datalog, '/pose/fieldToOdom', Pose3d)
            self.logOdomToRobot = StructLogEntry(datalog, '/pose/odomToRobot', Transform3d)

        self.clock = clock
        self._last_o2r = Transform3d()
        "Last odometry->robot (cache)"

        self.buf_field_to_robot = TimeInterpolatablePose3dBuffer(config.pose_history.seconds, interpolate_pose3d)
        self.buf_field_to_odom = TimeInterpolatablePose3dBuffer(config.pose_history.seconds, interpolate_pose3d)
    
    def odom_to_robot(self) -> Transform3d:
        "Get the best estimated `odom`→`robot` corrective transform"
        samples_f2o = self.buf_field_to_odom.getInternalBuffer()
        samples_f2r = self.buf_field_to_robot.getInternalBuffer()
        # Return identity if we don't have any data
        if (len(samples_f2o) == 0) or (len(samples_f2r) == 0):
            return self._last_o2r
        
        # Find timestamps of overlapping range between field->odom and field->robot data
        ts_start = max(samples_f2o[0][0], samples_f2r[0][0])
        ts_end = min(samples_f2o[-1][0], samples_f2r[-1][0])
        if ts_end < ts_start:
            # No overlap
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
        return self.buf_field_to_robot.sample(time.as_seconds()) or Pose3d()
    
    def field_to_odom(self, time: Timestamp) -> Pose3d:
        "Get the `field`→`odom` transform at a specified time"
        return self.buf_field_to_odom.sample(time.as_seconds()) or Pose3d()
    
    def record_f2r(self, robot_to_camera: Transform3d, msg: MsgPose):
        "Record SLAM pose"
        field_to_camera = msg.pose
        field_to_robot = field_to_camera.transformBy(robot_to_camera.inverse())
        timestamp = Timestamp.from_nanos(msg.timestamp)

        if self.datalog is not None:
            self.logFieldToRobot.append(field_to_robot, timestamp.as_wpi())
        
        self.buf_field_to_robot.addSample(timestamp.as_seconds(), field_to_robot)
    
    def record_f2o(self, timestamp: int, field_to_odom: Pose3d):
        "Record odometry pose"
        ts = Timestamp.from_nanos(timestamp)
        if self.datalog is not None:
            self.logFieldToOdom.append(field_to_odom, ts.as_wpi())
        
        self.buf_field_to_odom.addSample(ts.as_seconds(), field_to_odom)
    
    def clear(self):
        self.buf_field_to_odom.clear()
        self.buf_field_to_robot.clear()
        self._last_o2r = Transform3d()


class DataFusion:
    pose_estimator: PoseEstimator
    object_tracker: ObjectTracker

    def __init__(self, *, config: EstimatorConfig, log: Optional[logging.Logger], datalog: Optional[DataLog] = None, clock: Optional[Clock] = None) -> None:
        self.log = logging.getLogger("data") if log is None else log.getChild("data")
        self.datalog = datalog
        self.clock = clock or MonoClock()
        self.config = config

        self.pose_estimator = PoseEstimator(config, self.clock, log=self.log, datalog=self.datalog)
        self.object_tracker = ObjectTracker(config)

    def transform_detections(self, robot_to_camera: Transform3d, detections: MsgDetections, mapper_loc: Optional[TimeMapper] = None, mapper_net: Optional[TimeMapper] = None) -> net.ObjectDetections:
        "Transform detections message into robot-space"
        if mapper_loc is not None:
            assert mapper_loc.clock_b == self.clock
        if mapper_net is not None:
            assert mapper_loc.clock_a == self.clock
        
        # I'm not super happy with this method being on PoseEstimator, but whatever
        labels: OrderedDict[str, int] = OrderedDict()
        res: List[net.ObjectDetection] = list()
        timestamp     = detections.timestamp
        timestamp_loc = timestamp     if (mapper_loc is None) else mapper_loc.a_to_b(timestamp)
        timestamp_net = timestamp_loc if (mapper_net is None) else mapper_net.a_to_b(timestamp_loc)

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
                timestamp=net.Timestamp(timestamp_net // 1_000_000_000, timestamp_net % 1_000_000_000),
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