from typing import overload
import numpy as np
from wpimath.geometry import CoordinateSystem

from typedef.geom import Rotation3d, Transform3d, Pose3d, Twist3d, Translation3d


APRILTAG_BASE_ROTATION = Rotation3d(np.array([0,1,0]), np.deg2rad(180))
"""
From the AprilTag repo:
"The coordinate system has the origin at the camera center. The z-axis points from the camera
center out the camera lens. The x-axis is to the right in the image taken by the camera, and
y is down. The tag's coordinate frame is centered at the center of the tag, with x-axis to the
right, y-axis down, and z-axis into the tag."

This means our detected transformation will be in EDN. Our subsequent uses of the transformation,
however, assume the tag's z-axis point away from the tag instead of into it. This means we
have to correct the transformation's rotation.
"""

def apriltag_to_cv2(tf_at: Transform3d) -> Transform3d:
	"""
	AprilTag returns a camera-to-tag transform in EDN, but the tag's z-axis points into the tag
	instead of away from it and towards the camera. This means we have to correct the
	transformation's rotation.

	@param pose The Transform3d with translation and rotation directly from the [AprilTagPoseEstimate]
	"""
	rot_cv2 = APRILTAG_BASE_ROTATION.rotateBy(tf_at.rotation())
	return Transform3d(
		tf_at.translation(),
		rot_cv2,
	)

def cv2_to_apriltag(tf_cv2: Transform3d) -> Transform3d:
	rot_at = Rotation3d(0, np.pi, 0) + tf_cv2.rotation()
	return Transform3d(
		tf_cv2.translation(),
		rot_at,
    )

@overload
def wpi_to_cv2(tf_wpi: Transform3d) -> Transform3d: ...
@overload
def wpi_to_cv2(tf_wpi: Pose3d) -> Pose3d: ...
@overload
def wpi_to_cv2(tf_wpi: Rotation3d) -> Rotation3d: ...
@overload
def wpi_to_cv2(tf_wpi: Translation3d) -> Translation3d: ...
def wpi_to_cv2(tf_wpi: Transform3d | Pose3d | Rotation3d | Translation3d):
	return CoordinateSystem.convert(tf_wpi, CoordinateSystem.NWU(), CoordinateSystem.EDN())

@overload
def cv2_to_wpi(tf_cv2: Transform3d, /) -> Transform3d: ...
@overload
def cv2_to_wpi(tf_cv2: Pose3d, /) -> Pose3d: ...
@overload
def cv2_to_wpi(tf_cv2: Rotation3d, /) -> Rotation3d: ...
def cv2_to_wpi(arg0: Transform3d | Pose3d | Rotation3d, /):
	return CoordinateSystem.convert(arg0, CoordinateSystem.EDN(), CoordinateSystem.NWU())