from typing import TYPE_CHECKING, TypeVar, Type, Optional
if TYPE_CHECKING:
	from wpiutil.wpistruct import StructDescriptor
from .wpistruct import _get_sd
from .repr import FieldDesc, lookup_fields

T = TypeVar('T')

STRUCT_LUT = []
def _pickle_unpack_struct(idx: int, value: bytes):
	t = STRUCT_LUT[idx]
	desc = _get_sd(t)
	return desc.unpack(value)

def add_pickle_with_wpistruct(t: Type[T], sd: 'StructDescriptor'):
	"Add pickle support for a type, serializing it into its wpistruct representation"
	if t in STRUCT_LUT:
		return
	
	idx = len(STRUCT_LUT)
	STRUCT_LUT.append(t)

	def _reduce(self: T):
		ser = sd.pack(self)
		return (_pickle_unpack_struct, (idx, ser))
	t.__reduce__ = _reduce

FIELDORDER_LUT: list[Type] = []
def _dict_unpack_struct(idx: int, *args):
	type = FIELDORDER_LUT[idx]
	return type(*args)

def add_pickle_dict(t: Type[T], fields: list[FieldDesc]):
	# Pickle with dict
	idx = len(FIELDORDER_LUT)
	FIELDORDER_LUT.append(t)
	def _reduce(self: T):
		values = list(lookup_fields(fields, self))
		return (_dict_unpack_struct, (idx, *values))
	t.__reduce__ = _reduce

def add_pickle_support(t: Type[T], fields: list, sd: Optional['StructDescriptor'] = None):
	"Add pickle support for a type"
	if sd is None:
		try:
			sd = _get_sd(t)
		except AttributeError:
			pass
	
	if sd is not None:
		add_pickle_with_wpistruct(t, sd)
	else:
		add_pickle_dict(t, fields)
