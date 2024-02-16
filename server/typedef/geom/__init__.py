"""
Add compatibility with wpimath.geometry types

This file *modifies* (hopefully safely) the native wpimath geometry times to add support for:
 - Universal struct serialization
 - Pydantic JSON
 - pickle
"""
from .impl import (
	Quaternion,
	Rotation2d, Rotation3d,
	Translation2d, Translation3d,
	Transform2d, Transform3d,
	Pose2d, Pose3d,
	Twist2d, Twist3d,
)

__all__ = (
	'Quaternion',
	'Rotation2d', 'Rotation3d',
	'Translation2d', 'Translation3d',
	'Transform2d', 'Transform3d',
	'Pose2d', 'Pose3d',
	'Twist2d', 'Twist3d',
)