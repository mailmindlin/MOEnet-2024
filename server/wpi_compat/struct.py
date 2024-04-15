"Helpers for dealing with WPIstruct data"
from typing import TYPE_CHECKING, Protocol, ClassVar, Any, TypeVar, Type, Union, Never, overload, runtime_checkable
from wpiutil import wpistruct
from util.timestamp import Timestamp

if TYPE_CHECKING:
    from .typedef import SchemaRegistry

@runtime_checkable
class StructSerializable(Protocol):
    WPIStruct: ClassVar[Any]


class StructDescriptorBuilder:
    def add_field(self, name: str, type: type):
        pass

T = TypeVar('T', bound=StructSerializable)

@overload
def get_descriptor(type: type[StructSerializable]) -> wpistruct.StructDescriptor: ...
@overload
def get_descriptor(type: Any) -> Union[Never, wpistruct.StructDescriptor]: ...
def get_descriptor[T: StructSerializable](type: type[T]) -> wpistruct.StructDescriptor:
    """
    Get StructDescriptor for type

    :raises: TypeError: If `type` does not have an associated struct
    """

    if generated := getattr(type, '_WPIStruct', None):
        assert isinstance(generated, wpistruct.StructDescriptor)
        return generated
    if raw := getattr(type, 'WPIStruct', None):
        if isinstance(raw, wpistruct.StructDescriptor):
            return raw
    
    # Get from native code
    return wpistruct.StructDescriptor(
        typeString=wpistruct.getTypeString(type),
        schema=wpistruct.getSchema(type),
        size=wpistruct.getSize(type),
        pack=wpistruct.pack,
        packInto=wpistruct.packInto,
        unpack=lambda buffer: wpistruct.unpack(type, buffer),
        forEachNested=lambda callback: wpistruct.forEachNested(type, callback),
    )

def add_schema(registry: 'SchemaRegistry', type: Type[T], timestamp: Union[int, Timestamp, None] = None):
    """
    Register struct schema with a registry

    Parameters:
     - registry: SchemaRegistry
     - type: T
     - timestamp: int
    """

    if timestamp is None:
        timestamp = 0
    else:
        timestamp = Timestamp.wrap_wpi(timestamp).as_wpi()

    sd = get_descriptor(type)
    if registry.hasSchema(sd.typeString):
        return sd.typeString
    # Add main schema
    registry.addSchema(sd.typeString, "structschema", sd.schema, timestamp)
    if sd.forEachNested is not None:
        def handle_nested(nested_tstr: str, nested_schema: str):
            if registry.hasSchema(nested_tstr):
                return
            registry.addSchema(nested_tstr, "structschema", nested_schema, timestamp)
        sd.forEachNested(handle_nested)
    
    return sd.typeString