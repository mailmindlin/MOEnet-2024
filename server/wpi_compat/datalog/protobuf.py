from typing import TypeVar, Type, TYPE_CHECKING, List
from wpiutil.log import DataLog
from .. import protobuf
from .wrappers import WrappedLogEntry

T = TypeVar('T')

class ProtoLogEntry(WrappedLogEntry[T]):
    def __init__(self, log: DataLog, name: str, type: Type[T], metadata: str = '', timestamp: int = 0):
        protobuf.add_schema(log, type, timestamp)
        super().__init__(log, name, protobuf.type_string(type), metadata, timestamp)
        self._type = type
    
    def _serialize(self, data: T) -> bytes:
        ser: bytes = data.SerializeToString()
        return ser
