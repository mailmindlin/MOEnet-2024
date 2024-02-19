from typing import TYPE_CHECKING, TypeVar, Type, Optional
if TYPE_CHECKING:
	from wpiutil.wpistruct import StructDescriptor
from wpi_compat.struct import get_descriptor
from .repr import FieldDesc, lookup_fields

T = TypeVar('T')

STRUCT_LUT = []
def _pickle_unpack_struct(idx: int, value: bytes):
	t = STRUCT_LUT[idx]
	desc = get_descriptor(t)
	return desc.unpack(value)

def add_pickle_with_wpistruct(t: Type[T], sd: 'StructDescriptor', reduce: bool = True, add_hash: bool = False):
	"Add pickle support for a type, serializing it into its wpistruct representation"
	if t in STRUCT_LUT:
		return
	
	idx = len(STRUCT_LUT)
	STRUCT_LUT.append(t)

	if reduce:
		def _reduce(self: T):
			ser = sd.pack(self)
			return (_pickle_unpack_struct, (idx, ser))
		t.__reduce__ = _reduce
	
	if add_hash:
		def _hash(self: T):
			ser = sd.pack(self)
			return hash(ser)
		t.__hash__ = _hash

FIELDORDER_LUT: list[Type] = []
def _dict_unpack_struct(idx: int, *args):
	type = FIELDORDER_LUT[idx]
	return type(*args)

def add_pickle_dict(t: Type[T], fields: list[FieldDesc], reduce: bool = True, add_hash: bool = False):
	# Pickle with dict
	idx = len(FIELDORDER_LUT)
	FIELDORDER_LUT.append(t)
	if reduce:
		def _reduce(self: T):
			values = list(lookup_fields(fields, self))
			return (_dict_unpack_struct, (idx, *values))
		t.__reduce__ = _reduce

	if add_hash:
		def _hash(self: T):
			values = tuple(lookup_fields(fields, self))
			return hash(values)
		t.__hash__ = _hash

def add_pickle_support(t: Type[T], fields: list, sd: Optional['StructDescriptor'] = None, *, reduce: bool = True, hash: bool = False):
	"Add pickle support for a type"
	if sd is None:
		try:
			sd = get_descriptor(t)
		except AttributeError:
			pass
	
	if sd is not None:
		add_pickle_with_wpistruct(t, sd, reduce=reduce, add_hash=hash)
	else:
		add_pickle_dict(t, fields, reduce=reduce, add_hash=hash)
