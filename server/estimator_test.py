from unittest import TestCase
from estimator import PoseEstimator, Transform3d, MsgPose, Pose3d, Rotation3d, Translation3d, Clock, Twist3d
from typedef.geom import Pose3d, Twist3d, Translation3d
# Tests
class PoseEstimatorTest(TestCase):
    def setUp(self) -> None:
        class FakeClock(Clock):
            def __init__(self) -> None:
                super().__init__()
                self.time = 0
            def now(self):
                return self.time
        self.clock = FakeClock()
    
    def test_interpolate(self):
        estimator = PoseEstimator(
            clock=self.clock,
            history_duration=10.0
        )
        f2r_0 = Pose3d(Translation3d(0, 0, 0), Rotation3d())
        f2r_2 = Pose3d(Translation3d(2, 0, 0), Rotation3d())
        estimator.record_f2r(Transform3d(), MsgPose(timestamp=0, view_mat=None, pose=f2r_0, poseCovariance=None, twist=Twist3d(), twistCovariance=None))
        estimator.record_f2r(Transform3d(), MsgPose(timestamp=int(2e9), view_mat=None, pose=f2r_2, poseCovariance=None, twist=Twist3d(), twistCovariance=None))
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