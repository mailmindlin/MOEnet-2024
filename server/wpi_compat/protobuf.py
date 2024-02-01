"Helpers for serializing protobuf-valued types"

from typing import TYPE_CHECKING, Callable, Iterable

if TYPE_CHECKING:
	from google.protobuf.pyext.cpp_message import GeneratedProtocolMessageType
	from google.protobuf.descriptor import FileDescriptor
	from .typedef import SchemaRegistry


def type_string(proto: 'GeneratedProtocolMessageType') -> str:
	if name := getattr(proto, 'type_string', None):
		return name
	return 'proto:' + proto.DESCRIPTOR.name

def _iter_descriptor(file: 'FileDescriptor', exists: Callable[[str], bool]) -> Iterable[tuple[str, bytes]]:
	"Iterate (recursively) through FileDescriptor schemas"
	name = "proto:" + file.name #TODO: is this file.package + file.name?
	if exists(name):
		return
	for dep in file.dependencies:
		# Recurse
		yield from _iter_descriptor(dep, exists)
	yield (name, file.serialized_pb)

def add_schema(registry: 'SchemaRegistry', proto: 'GeneratedProtocolMessageType'):
	"Register a protobuf's schema with NetworkTables"
	for (typeString, schema) in _iter_descriptor(proto.DESCRIPTOR.file, registry.hasSchema):
		registry.addSchema(typeString, "proto:FileDescriptorProto", schema)