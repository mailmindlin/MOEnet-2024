from typing import List, Optional
from typedef.worker import MsgPose, MsgDetections
from typedef.geom import Pose, Twist, Vector3
from typedef import net
from clock import Clock, MonoClock, TimeMapper
from wpimath.geometry import Transform3d, Translation3d, Rotation3d, Pose3d
from wpimath.interpolation._interpolation import TimeInterpolatablePose3dBuffer
from wpimath.units import seconds
from collections import OrderedDict

def interpolate_pose3d(a: Pose3d, b: Pose3d, t: float) -> Pose3d:
    "Interpolate between `Pose3d`s"
    if t <= 0:
        return a
    if t >= 1:
        return b
    twist = a.log(b)
    return a.exp(twist * t)


class PoseEstimator:
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
    
    def transform_detections(self, robot_to_camera: Transform3d, detections: MsgDetections, mapper_loc: Optional[TimeMapper] = None, mapper_net: Optional[TimeMapper] = None) -> net.Detections:
        "Transform detections message into robot-space"
        if mapper_loc is not None:
            assert mapper_loc.clock_b == self.clock
        if mapper_net is not None:
            assert mapper_loc.clock_a == self.clock
        
        # I'm not super happy with this method being on PoseEstimator, but whatever
        labels: OrderedDict[str, int] = OrderedDict()
        res: List[net.Detection] = list()
        timestamp     = detections.timestamp
        timestamp_loc = timestamp     if (mapper_loc is None) else mapper_loc.a_to_b(timestamp)
        timestamp_net = timestamp_loc if (mapper_net is None) else mapper_net.a_to_b(timestamp_loc)

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
            detection_net = net.Detection(
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
        
        return net.Detections(
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