from typing import List, Optional, TYPE_CHECKING, Dict
from collections import OrderedDict

import numpy as np
from wpimath.geometry import Transform3d, Translation3d, Rotation3d, Pose3d
from wpimath.interpolation._interpolation import TimeInterpolatablePose3dBuffer
from wpimath.units import seconds

from typedef.worker import MsgPose, MsgDetections, MsgDetection
from typedef.geom import Pose, Twist, Vector3
from typedef import net
from clock import Clock, MonoClock, TimeMapper


def interpolate_pose3d(a: Pose3d, b: Pose3d, t: float) -> Pose3d:
    "Interpolate between `Pose3d`s"
    if t <= 0:
        return a
    if t >= 1:
        return b
    twist = a.log(b)
    return a.exp(twist * t)



MIN_DETECTIONS = 8
DETECTION_WINDOW = 1.0
MAX_UNSEEN_AGE = 8.0
CLUSTERING_DISTANCE_AT_1M = 0.3
class TrackedObject:
    def __init__(self, id: int, timestamp: int, position: Translation3d, label: str, confidence: float):
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
    
    def should_remove(self, t: float):
        if self.n_detections < MIN_DETECTIONS and self.last_seen < t - DETECTION_WINDOW:
            return True
        if self.last_seen < t - MAX_UNSEEN_AGE:
            return True
        return False

    def __str__(self):
        return f'{self.label}@{self.id}'


class ObjectTracker:
    tracked_objects: Dict[str, List[TrackedObject]]

    def __init__(self, clustering_distance: float = 0.3, min_depth: float = 0.5) -> None:
        self.tracked_objects = dict()
        self._next_id = 0
        self.min_depth = min_depth
        self.clustering_distance = clustering_distance

    def _find_best_match(self, new_obj: TrackedObject, field_to_camera: Pose3d):
        new_cs = new_obj.position_rel(field_to_camera)

        best = None
        best_dist = self.clustering_distance
        for old in self.tracked_objects.setdefault(new_obj.label, []):
            # ignore depth difference in clustering
            old_cs = new_obj.position_rel(field_to_camera)

            # Distance away from camera
            z = max(self.min_depth, old_cs.z, new_cs.z)
            dist: float = np.hypot(old_cs.x - new_cs.x, old_cs.y - new_cs.y) / z

            if dist < best_dist:
                best_dist = dist
                best = old
        # if best: print(f'matched with {best} (seen {best.n_detections} time(s))')
        return best

    def track(self, t: float, detections: MsgDetections, field_to_robot: Pose3d, robot_to_camera: Transform3d):
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
                existing.update(new_obj)
            else:
                self._next_id += 1 # Only bump IDs for new objects
                self.tracked_objects.setdefault(label, []) \
                    .append(new_obj)
    
    def cleanup(self, t: float):
        # remove cruft
        tracked_objects: Dict[str, List[TrackedObject]] = dict()
        for key, value in self.tracked_objects.items():
            value1 = [
                obj
                for obj in value
                if not obj.should_remove(t)
            ]
            if len(value1) > 0:
                tracked_objects[key] = value1
        self.tracked_objects = tracked_objects
    
    def items(self):
        return (
            o
            for l in self.tracked_objects.values()
            for o in l
            if o.n_detections >= MIN_DETECTIONS
        )

    def clear(self):
        self.tracked_objects.clear()


class PoseEstimator:
    """
    We need to merge together (often) conflicting views of the world.
    """
    def __init__(self, *, clock: Optional[Clock] = None, history_duration: seconds = 5.0) -> None:
        self.clock = clock if (clock is not None) else MonoClock()
        self._last_o2r = None
        self.buf_field_to_robot = TimeInterpolatablePose3dBuffer(history_duration, interpolate_pose3d)
        self.buf_field_to_odom = TimeInterpolatablePose3dBuffer(history_duration, interpolate_pose3d)
    
    def odom_to_robot(self) -> Transform3d:
        "Get the best estimated `odom`→`robot` corrective transform"
        samples_f2o = self.buf_field_to_odom.getInternalBuffer()
        samples_f2r = self.buf_field_to_robot.getInternalBuffer()
        # Return identity if we don't have any data
        if (len(samples_f2o) == 0) or (len(samples_f2r) == 0):
            return Transform3d()
        
        # Find timestamps of overlapping range between field->odom and field->robot data
        ts_start = max(samples_f2o[0][0], samples_f2r[0][0])
        ts_end = min(samples_f2o[-1][0], samples_f2r[-1][0])
        if ts_end < ts_start:
            # No overlap
            return self._last_o2r or Transform3d()
        
        # We want the most recent pair that overlap
        f2o = self.buf_field_to_odom.sample(ts_end)
        assert f2o is not None
        f2r = self.buf_field_to_robot.sample(ts_end)
        assert f2r is not None
        
        res = Transform3d(f2o, f2r)
        self._last_o2r = res
        return res
    
    def field_to_robot(self, time: int) -> Pose3d:
        "Get the `field`→`robot` transform at a specified time"
        return self.buf_field_to_robot.sample(time / 1e9) or Pose3d()
    
    def field_to_odom(self, time: int) -> Pose3d:
        "Get the `field`→`odom` transform at a specified time"
        return self.buf_field_to_odom.sample(time / 1e9) or Pose3d()

    def record_f2r(self, robot_to_camera: Transform3d, msg: MsgPose):
        "Record SLAM pose"
        field_to_camera = msg.pose.as_pose()
        field_to_robot = field_to_camera.transformBy(robot_to_camera.inverse())
        timestamp = msg.timestamp / 1e9
        self.buf_field_to_robot.addSample(timestamp, field_to_robot)
    
    def record_f2o(self, timestamp: int, odom: Pose3d):
        "Record odometry pose"
        timestamp = timestamp / 1e9
        self.buf_field_to_odom.addSample(timestamp, odom)
    
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
        timestamp_net = net.Timestamp(
            seconds=int(timestamp_net / 1e9),
            nanos=int(timestamp_net % 1e9),
        )

        field_to_robot = Transform3d(Pose3d(), self.field_to_robot(timestamp_loc))
        field_to_camera = field_to_robot + robot_to_camera

        for detection in detections.detections:
            # Lookup or get next ID
            label_id = labels.setdefault(detection.label, len(labels))

            # Compute transforms
            camera_to_object = Transform3d(detection.position.as_wpi(), Rotation3d())
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
    
    def clear(self):
        self.buf_field_to_odom.clear()
        self.buf_field_to_robot.clear()
        self._last_o2r = None


# Tests
if __name__ == '__main__':
    class FakeClock(Clock):
        def __init__(self) -> None:
            super().__init__()
            self.time = 0
        def now(self):
            return self.time
    
    estimator = PoseEstimator(
        clock=FakeClock(),
        history_duration=10.0
    )
    f2r_0 = Pose(translation=Vector3(x=0.0))
    f2r_2 = Pose(translation=Vector3(x=2.0))
    estimator.record_f2r(Transform3d(), MsgPose(timestamp=0, view_mat=None, pose=f2r_0, poseCovariance=None, twist=Twist(), twistCovariance=None))
    estimator.record_f2r(Transform3d(), MsgPose(timestamp=int(2e9), view_mat=None, pose=f2r_2, poseCovariance=None, twist=Twist(), twistCovariance=None))
    assert estimator.field_to_robot(0) == Pose3d()
    assert estimator.field_to_robot(2e9) == Pose3d(Translation3d(x=2,y=0,z=0), Rotation3d())
    # Check lerp
    assert estimator.field_to_robot(1e9) == Pose3d(Translation3d(x=1,y=0,z=0), Rotation3d())

    # We haven't provided any odometry info, so it should be empty
    assert estimator.odom_to_robot() == Transform3d()

    # Provide odometry
    f2o_1 = Pose3d(Translation3d(x=1,y=1,z=0), Rotation3d())
    estimator.record_f2o(1e9, f2o_1)

    f2r_1 = estimator.field_to_robot(1e9) # Correct value
    o2r_1 = estimator.odom_to_robot()
    f2r_1_ = f2o_1 + o2r_1 # Apply odometry correction
    assert f2r_1 == f2r_1_