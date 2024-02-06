from typing import TypeVar, Generic
from wpiutil.log import DataLog, RawLogEntry
from abc import ABC, abstractmethod

T = TypeVar('T')

class WrappedLogEntry(Generic[T], ABC):
    "Log a serializable data to [DataLog]"
    def __init__(self, log: DataLog, name: str, type_string: str, metadata: str = '', timestamp: int = 0):
        self._raw = RawLogEntry(log, name, type_string, metadata, timestamp)
    
    @abstractmethod
    def _serialize(self, data: T) -> bytes:
        "Serialize data"
        ...
    
    def append(self, data: T, timestamp: int = 0) -> None:
        ser = self._serialize(data)
        self._raw.append(ser, timestamp)
    
    def finish(self, timestamp: int = 0) -> None:
        self._raw.finish(timestamp)
    
    def setMetadata(self, metadata: str, timestamp: int = 0) -> None:
        self._raw.setMetadata(metadata, timestamp)