"""
Add compatibility with wpimath.geometry types
"""
from typing import TYPE_CHECKING, Type, TypeVar, Tuple, Any, List, Union, Dict, Optional, Generic, Callable
from struct import Struct
from dataclasses import dataclass
from pydantic_core import core_schema
from pydantic import (
	GetCoreSchemaHandler,
	GetJsonSchemaHandler,
	ValidationError,
)
from pydantic.json_schema import JsonSchemaValue

from wpimath.geometry import (
	Rotation2d, Rotation3d,
	Translation2d, Translation3d,
	Transform2d, Transform3d,
	Pose2d, Pose3d,
	Twist2d, Twist3d,
	Quaternion,
)
from wpiutil import wpistruct
from wpiutil.wpistruct import StructDescriptor
from wpiutil.wpistruct.dataclass import _type_to_fmt

if TYPE_CHECKING:
	from typing_extensions import Buffer



# ===== Utilities =====
T = TypeVar('T')
F = TypeVar('F')

@dataclass
class FieldDesc:
	type: Type
	getter: Optional[str] = None


@dataclass
class FieldInfo(Generic[T, F]):
	@staticmethod
	def wrap(name: str, base: Type[T], value: Union[Type[F], FieldDesc]) -> 'FieldInfo[T, F]':
		getter = None
		if isinstance(value, FieldDesc):
			type = value.type
			getter = value.getter
		else:
			type = value
		return FieldInfo(
			name=name,
			base=base,
			type=type,
			getter=getter
		)
	
	name: str
	base: Type[T]
	type: Type[F]
	getter: Optional[str] = None

	def doc(self) -> Optional[str]:
		if entry := getattr(self.base, self.name, None):
			if doc := getattr(entry, '__doc__', None):
				return doc

	def get(self, value: T) -> F:
		name = self.getter if self.getter is not None else self.name
		res = getattr(value, name)
		if callable(res):
			res = res()
		return res


def _lookup_fields(fields: List[FieldInfo[T, Any]], value: T):
	"Get named fields as a list"
	for field in fields:
		yield field.get(value)



# ===== Structs =====
def _build_sd(t: Type[T], s: Struct, schema: str, fields: List[FieldInfo[T, Any]]):
	"Build StructDescriptor. Called by fix_struct (saves memory by preserving a smaller scope)"
	name = f'struct:{t.__name__}'
	
	def _pack(value: T) -> bytes:
		return s.pack(*_lookup_fields(fields, value))
	
	def _packinto(value: T, buffer: 'Buffer'):
		return s.pack_into(
			buffer,
			0,
			*_lookup_fields(fields, value)
		)
	
	def _unpack(b: 'Buffer') -> T:
		values = s.unpack(b)
		return t(**{
			field.name: value
			for field, value in zip(fields, values)
		})
	return StructDescriptor(
		name,
		schema,
		s.size,
		_pack,
		_packinto,
		_unpack,
		None
	)

def fix_struct(t: Type[T], fields: List[FieldInfo]):
	"Fixes types missing WPIStruct"
	fmts = []
	schema = []
	for field in fields:
		ftype = field.type
		if ftype in _type_to_fmt:
			fmt, stype = _type_to_fmt[ftype]

			fmts.append(fmt)
			schema.append(f"{stype} {field.name}")
	
	s = Struct(f"<{''.join(fmts)}")
	sd = _build_sd(t, s, "; ".join(schema), fields)
	if not getattr(t, 'WPIStruct', None):
		t.WPIStruct = sd
	t._WPIStruct = sd
	return sd

def _get_sd(t: Type[T]) -> StructDescriptor:
	"Get StructDescriptor for type (we might store it in two fields, depending)"
	# if r := getattr(t, 'WPIStruct', None):
	# 	if isinstance(r, StructDescriptor):
	# 		return r
	return getattr(t, '_WPIStruct')


# ===== Pickle fixes =====
STRUCT_LUT = []
def _pickle_unpack_struct(idx: int, value: bytes):
	t = STRUCT_LUT[idx]
	desc = _get_sd(t)
	return desc.unpack(value)
def _build_pickle_struct(t: Type[T], sd: StructDescriptor):
	if t in STRUCT_LUT:
		return
	
	idx = len(STRUCT_LUT)
	STRUCT_LUT.append(t)

	def _reduce(self: T):
		ser = sd.pack(self)
		return (_pickle_unpack_struct, (idx, ser))
	t.__reduce__ = _reduce
FIELDORDER_LUT: List[Type] = []
def _dict_unpack_struct(idx: int, *args):
	type = FIELDORDER_LUT[idx]
	return type(*args)


# ===== JSON fixes =====
SCHEMA_LUT = {
	int: core_schema.int_schema(),
	float: core_schema.float_schema(),
	wpistruct.double: core_schema.float_schema(),
}
@dataclass
class CustomSchemaInfo:
	schema: Any
	serialize_json: Callable[[Any], Any]
	parse_json: Callable[[Any], Any]
CUSTOM_SCHEMA: Dict[str, CustomSchemaInfo] = dict()

def make_pydantic_validator(t: Type[T], fields: List[FieldInfo]):
	tdfs = dict()
	for field in fields:
		base = SCHEMA_LUT.get(field.type, None) or CUSTOM_SCHEMA[field.type].schema
		# print(f'Map field {t.__name__}.{field.name} -> {base}')
		tdf = core_schema.typed_dict_field(base, required=True)
		#TODO: figure out how to set description fields
		# if desc := field.doc():
		# 	print(f'Map field {t.__name__}.{field.name} -> {desc}')
		# 	tdf['description'] = desc
		tdfs[field.name] = tdf
	schema = core_schema.typed_dict_schema(tdfs)

	def serialize_json(value: T):
		res = dict()
		for field in fields:
			fval = field.get(value)
			if custom := CUSTOM_SCHEMA.get(field.type, None):
				fval = custom.serialize_json(fval)
			res[field.name] = fval
		return res

	def parse_json(raw: Any):
		print('raw', raw)
		values = list()
		for field in fields:
			value = raw[field.name]
			if custom := CUSTOM_SCHEMA.get(field.type, None):
				value = custom.parse_json(value)
			values.append(value)
		return t(*values)
	

	CUSTOM_SCHEMA[t] = CustomSchemaInfo(schema=schema, serialize_json=serialize_json, parse_json=parse_json)

	@classmethod
	def __get_pydantic_core_schema__(
		cls: Type[T],
		_source_type: Any,
		_handler: GetCoreSchemaHandler,
	) -> core_schema.CoreSchema:
		json_schema = core_schema.chain_schema(
			[
				schema,
				core_schema.no_info_plain_validator_function(parse_json),
			]
		)

		return core_schema.json_or_python_schema(
			json_schema=json_schema,
			python_schema=core_schema.union_schema(
				[
					# check if it's an instance first before doing any further work
					core_schema.is_instance_schema(t),
					json_schema,
				]
			),
			serialization=core_schema.plain_serializer_function_ser_schema(serialize_json),
		)

	@classmethod
	def __get_pydantic_json_schema__(cls: Type[T], _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
		return handler(schema)
	
	t.__get_pydantic_core_schema__ = __get_pydantic_core_schema__
	t.__get_pydantic_json_schema__ = __get_pydantic_json_schema__

def fix_ser(t: Type[T], fields: Dict[str, Union[FieldDesc, Type]], *, struct: bool = False, pickle: bool = True, json: bool = True):
	fields = [
		FieldInfo.wrap(fname, t, fval)
		for fname, fval in fields.items()
	]

	sd = None
	if struct:
		sd = fix_struct(t, fields)
	
	if pickle:
		if sd is None:
			try:
				sd = _get_sd(t)
			except AttributeError:
				pass
		
		if sd is not None:
			_build_pickle_struct(t, sd)
		else:
			# Pickle with dict
			idx = len(FIELDORDER_LUT)
			FIELDORDER_LUT.append(t)
			def _reduce(self: T):
				values = list(_lookup_fields(fields, self))
				return (_dict_unpack_struct, (idx, *values))
			t.__reduce__ = _reduce
	
	if json:
		make_pydantic_validator(t, fields)

fix_ser(Translation2d, {
	'x': wpistruct.double,
	'y': wpistruct.double,
}, struct=True)
fix_ser(Rotation2d, {
	'radians': wpistruct.double,
})
fix_ser(Transform2d, {
	'translation': Translation2d,
	'rotation': Rotation2d,
})
fix_ser(Pose2d, {
	'translation': Translation2d,
	'rotation': Rotation2d,
})
fix_ser(Twist2d, {
	'dx': wpistruct.double,
	'dy': wpistruct.double,
	'dtheta': wpistruct.double,
})
fix_ser(Translation3d, {
	'x': wpistruct.double,
	'y': wpistruct.double,
	'z': wpistruct.double,
}, struct=True)
fix_ser(Quaternion, {
	'W': wpistruct.double,
	'X': wpistruct.double,
	'Y': wpistruct.double,
	'Z': wpistruct.double,
})
fix_ser(Rotation3d, {
	'quaternion': FieldDesc(getter='getQuaternion', type=Quaternion)
})
fix_ser(Transform3d, {
	'translation': Translation3d,
	'rotation': Rotation3d,
})
fix_ser(Pose3d, {
	'translation': Translation3d,
	'rotation': Rotation3d,
})
fix_ser(Twist3d, {
	'dx': wpistruct.double,
	'dy': wpistruct.double,
	'dz': wpistruct.double,
	'rx': wpistruct.double,
	'ry': wpistruct.double,
	'rz': wpistruct.double,
}, struct=True, pickle=True)