from typing import TypeVar, Type, TYPE_CHECKING, List
from wpiutil.log import DataLog
from .. import struct
from .wrappers import WrappedLogEntry

T = TypeVar('T')

class StructLogEntry(WrappedLogEntry[T]):
    "Log a `WpiStruct`-valued data to [DataLog]"
    def __init__(self, log: DataLog, name: str, type: Type[T], metadata: str = '', timestamp: int = 0):
        type_string = struct.add_schema(log, type, timestamp)
        super().__init__(log, name, type_string, metadata, timestamp)
        self._sd = struct.get_descriptor(type)
    
    def _serialize(self, data: T) -> bytes:
        return self._sd.pack(data)

class StructArrayLogEntry(WrappedLogEntry[list[T]]):
    "Log a `Array<WpiStruct>`-valued data to [DataLog]"
    def __init__(self, log: DataLog, name: str, type: Type[T], metadata: str = '', timestamp: int = 0):
        type_string = struct.add_schema(log, type, timestamp)
        super().__init__(log, name, type_string + "[]", metadata, timestamp)
        self._sd = struct.get_descriptor(type)
    
    def _serialize(self, data: list[T]) -> bytes:
        if not isinstance(data, list):
            raise TypeError(f'Unexpected data: {repr(data)}')
        
        return b''.join(self._sd.pack(entry) for entry in data)