from unittest import TestCase
from datetime import timedelta

from util.timestamp import Timestamp, Stamped
from typedef.geom import Pose3d, Translation3d
from typedef.geom_cov import Pose3dCov
from typedef.cfg import PoseEstimatorConfig

from .pose_simple import (
    SimplePoseEstimator,
    Transform3d,
    Pose3d, Rotation3d, Translation3d,
    Clock,
)
from .util.cascade import StaticValue


class PoseEstimatorTest(TestCase):
    def setUp(self) -> None:
        # Create a clock that doesn't update
        class FakeClock(Clock):
            def __init__(self) -> None:
                super().__init__()
                self.time = 0
            def now_ns(self):
                return self.time
        self.clock = FakeClock()
    
    def test_interpolate(self):
        estimator = SimplePoseEstimator(
            PoseEstimatorConfig(
                history=timedelta(seconds=10.0),
                force2d=False,
            ),
            clock=self.clock,
        )

        r2c = StaticValue(Transform3d())
        # Start at f2r (0, 0, 0) t=0
        f2r_0 = Pose3dCov(Pose3d(Translation3d(0, 0, 0), Rotation3d()))
        estimator.observe_f2r(Timestamp(0), r2c, f2r_0)
        # End at f2r (0, 0, 0) t=2s
        f2r_2 = Pose3dCov(Pose3d(Translation3d(2, 0, 0), Rotation3d()))
        estimator.observe_f2r(Timestamp.from_seconds(2), r2c, f2r_2)

        # Check simple lookups
        self.assertEqual(estimator.field_to_robot(Timestamp(0)), Pose3d())
        self.assertEqual(estimator.field_to_robot(Timestamp.from_seconds(2)), Pose3d(Translation3d(x=2,y=0,z=0), Rotation3d()))

        # Check lerp (t=1s)
        self.assertEqual(estimator.field_to_robot(Timestamp.from_seconds(1)), Pose3d(Translation3d(x=1,y=0,z=0), Rotation3d()))

        # We haven't provided any odometry info, so it should be empty
        self.assertEqual(estimator.latest_odom_to_robot().current.value, Transform3d())

    
    def test_correct(self):
        estimator = SimplePoseEstimator(
            PoseEstimatorConfig(
                history=timedelta(seconds=10.0),
                force2d=False,
            ),
            clock=self.clock,
        )
        r2c = StaticValue(Transform3d())
        # Start at f2r (0, 0, 0) t=0
        f2r_0 = Pose3dCov(Pose3d(Translation3d(0, 0, 0), Rotation3d()))
        estimator.observe_f2r(Timestamp(0), r2c, f2r_0)
        # End at f2r (2, 0, 0) t=2s
        f2r_2 = Pose3dCov(Pose3d(Translation3d(2, 0, 0), Rotation3d()))
        estimator.observe_f2r(Timestamp.from_seconds(2), r2c, f2r_2)

        # We haven't provided any odometry info, so it should be empty
        tr = estimator.latest_odom_to_robot()
        self.assertEqual(tr.current.value, Transform3d())
        self.assertTrue(tr.is_fresh)

        # Provide odometry (1,1,0) t=1
        f2o_1 = Pose3d(Translation3d(x=1,y=1,z=0), Rotation3d())
        estimator.observe_f2o(Timestamp.from_seconds(1), f2o_1)
        self.assertFalse(tr.is_fresh)
        self.assertEqual(estimator.field_to_odom(Timestamp.from_seconds(1)), f2o_1)

        # Correct robot position at t=1
        f2r_1 = estimator.field_to_robot(Timestamp.from_seconds(1))
        self.assertEqual(f2r_1, Pose3d(Translation3d(x=1,y=0,z=0), Rotation3d()))

        # Retrieve odometry correction
        o2r_1 = estimator.latest_odom_to_robot().current
        self.assertEqual(o2r_1.ts, Timestamp.from_seconds(1), "Overlap should be at t=1")
        self.assertEqual(o2r_1.value, Transform3d(Translation3d(0, -1, 0), Rotation3d()))
        
        f2r_1_ = f2o_1 + o2r_1.value # Apply odometry correction
        self.assertEqual(f2r_1, f2r_1_)