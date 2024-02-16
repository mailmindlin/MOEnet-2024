from typing import TYPE_CHECKING, Type, TypeVar, Any
if TYPE_CHECKING:
	from typing_extensions import Buffer
from struct import Struct

from wpiutil.wpistruct import StructDescriptor
from wpiutil.wpistruct.dataclass import _type_to_fmt # This is probably bad to do

from .repr import lookup_fields, FieldInfo

T = TypeVar('T')


def _build_sd(t: Type[T], s: Struct, schema: str, fields: list[FieldInfo[T, Any]]):
	"Build StructDescriptor. Called by fix_struct (saves memory by preserving a smaller scope)"
	name = f'struct:{t.__name__}'
	
	def _pack(value: T) -> bytes:
		return s.pack(*lookup_fields(fields, value))
	
	def _packinto(value: T, buffer: 'Buffer'):
		return s.pack_into(
			buffer,
			0,
			*lookup_fields(fields, value)
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

def fix_struct(t: Type[T], fields: list[FieldInfo]):
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