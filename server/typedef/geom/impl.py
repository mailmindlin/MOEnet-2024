from typing import Type, Union, TypeVar
from wpimath.geometry import (
	Quaternion,
	Rotation2d, Rotation3d,
	Translation2d, Translation3d,
	Transform2d, Transform3d,
	Pose2d, Pose3d,
	Twist2d, Twist3d,
)
from wpiutil import wpistruct
from .repr import FieldDesc

T = TypeVar('T')

def _fix_ser(t: Type[T], fields: dict[str, Union[FieldDesc, Type]], *, struct: bool = False, pickle: bool = True, json: bool = True, hash: bool = True):
	"""
	Fix type serialization, by modifying the datatypes
	"""
	from .repr import FieldInfo
	fields = [
		FieldInfo.wrap(fname, t, fval)
		for fname, fval in fields.items()
	]

	sd = None
	if struct:
		from .wpistruct import fix_struct
		sd = fix_struct(t, fields)
	
	if pickle or hash:
		from .pickle import add_pickle_support
		add_pickle_support(t, fields, sd, reduce=pickle, hash=hash)
		
	
	if json:
		from .pydantic import add_pydantic_validator
		add_pydantic_validator(t, fields)

# Translations are missing default struct impl
_fix_ser(Translation2d, {
	'x': wpistruct.double,
	'y': wpistruct.double,
}, struct=True)
_fix_ser(Translation3d, {
	'x': wpistruct.double,
	'y': wpistruct.double,
	'z': wpistruct.double,
}, struct=True)

_fix_ser(Rotation2d, {
	'radians': wpistruct.double,
})
_fix_ser(Quaternion, {
	'W': wpistruct.double,
	'X': wpistruct.double,
	'Y': wpistruct.double,
	'Z': wpistruct.double,
})
_fix_ser(Rotation3d, {
	# Serialize as quaternion (matches wpilib)
	'quaternion': FieldDesc(getter='getQuaternion', type=Quaternion)
})

_fix_ser(Transform2d, {
	'translation': Translation2d,
	'rotation': Rotation2d,
})
_fix_ser(Transform3d, {
	'translation': Translation3d,
	'rotation': Rotation3d,
})

_fix_ser(Pose2d, {
	'translation': Translation2d,
	'rotation': Rotation2d,
})
_fix_ser(Pose3d, {
	'translation': Translation3d,
	'rotation': Rotation3d,
})

_fix_ser(Twist2d, {
	'dx': wpistruct.double,
	'dy': wpistruct.double,
	'dtheta': wpistruct.double,
})
# Twist3d is missing default struct impl
_fix_ser(Twist3d, {
	'dx': wpistruct.double,
	'dy': wpistruct.double,
	'dz': wpistruct.double,
	'rx': wpistruct.double,
	'ry': wpistruct.double,
	'rz': wpistruct.double,
}, struct=True, pickle=True)
