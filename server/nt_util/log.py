from typing import TypeVar, Generic, Type, TYPE_CHECKING, Set, Optional
from wpiutil.log import DataLogEntry, DataLog, RawLogEntry
from typing_extensions import Buffer

if TYPE_CHECKING:
    from wpiutil.wpistruct import StructDescriptor

T = TypeVar('T')

def _add_schema(log: DataLog, ds: 'StructDescriptor', timestamp: int = 0, seen: Optional[Set[str]] = None):
    if seen is None:
        seen = set()
    if log.hasSchema(ds.typeString):
        return
    seen.add(ds.typeString)
    log.addSchema(ds.typeString, "structschema", ds.schema, timestamp)
    if ds.forEachNested is not None:
        raise NotImplementedError()
    seen.remove(ds.typeString)

class StructLogEntry(Generic[T]):
    def __init__(self, log: DataLog, name: str, type: Type[T], metadata: str = '', timestamp: int = 0):
        ds: 'StructDescriptor' = type._WPIStruct
        _add_schema(log, ds, timestamp)
        self._type = type
        self._raw = RawLogEntry(log, name, ds.typeString, metadata, timestamp)
    
    def append(self, data: T, timestamp: int = 0) -> None:
        """
        Appends a record to the log.
        
        :param data:      Data to record
        :param timestamp: Time stamp (may be 0 to indicate now)
        """
        ds: 'StructDescriptor' = self._type._WPIStruct
        ser = ds.pack(data)
        self._raw.append(ser, timestamp)
    
    """
    Log entry base class.
    """
    def finish(self, timestamp: int = 0) -> None:
        """
        Finishes the entry.
        
        :param timestamp: Time stamp (may be 0 to indicate now)
        """
        self._raw.finish(timestamp)
    
    def setMetadata(self, metadata: str, timestamp: int = 0) -> None:
        """
        Updates the metadata for the entry.
        
        :param metadata:  New metadata for the entry
        :param timestamp: Time stamp (may be 0 to indicate now)
        """
        self._raw.setMetadata(metadata, timestamp)