from typing import TypeVar, Generic, Type, TYPE_CHECKING, List
import logging
from wpiutil.log import DataLog, RawLogEntry, StringLogEntry
from wpiutil import wpistruct

if TYPE_CHECKING:
    from wpiutil.wpistruct import StructDescriptor
    from google.protobuf.pyext.cpp_message import GeneratedProtocolMessageType

T = TypeVar('T')

def _add_schema_struct(log: DataLog, t: type, timestamp: int = 0):
    if hasattr(t, '_WPIStruct'):
        if seen is None:
            seen = set()
        ds: 'StructDescriptor' = t._WPIStruct
        if log.hasSchema(ds.typeString):
            return ds.typeString
        seen.add(ds.typeString)
        log.addSchema(ds.typeString, "structschema", ds.schema, timestamp)
        if ds.forEachNested is not None:
            #TODO
            pass
        seen.remove(ds.typeString)
        return ds.typeString
    else:
        type_string = wpistruct.getTypeString(t)
        if log.hasSchema(type_string):
            return type_string
        log.addSchema(type_string, "structschema", wpistruct.getSchema(t), timestamp)
        def handle_nested(nested_tstr: str, nested_schema: str):
            if log.hasSchema(nested_tstr):
                return
            log.addSchema(nested_tstr, "structschema", nested_schema, timestamp)
        wpistruct.forEachNested(t, handle_nested)
        return type_string


class StructLogEntry(Generic[T]):
    def __init__(self, log: DataLog, name: str, type: Type[T], metadata: str = '', timestamp: int = 0):
        type_string = _add_schema_struct(log, type, timestamp)
        self._type = type
        self._raw = RawLogEntry(log, name, type_string, metadata, timestamp)
    
    def append(self, data: T, timestamp: int = 0) -> None:
        if (ds := getattr(self._type, '_WPIStruct', None)):
            ds: 'StructDescriptor'
            ser = ds.pack(data)
        else:
            ser = wpistruct.pack(data)
        self._raw.append(ser, timestamp)
    
    def finish(self, timestamp: int = 0) -> None:
        self._raw.finish(timestamp)
    
    def setMetadata(self, metadata: str, timestamp: int = 0) -> None:
        self._raw.setMetadata(metadata, timestamp)

class StructArrayLogEntry(Generic[T]):
    def __init__(self, log: DataLog, name: str, type: Type[T], metadata: str = '', timestamp: int = 0):
        type_string = _add_schema_struct(log, type, timestamp)
        self._type = type
        self._raw = RawLogEntry(log, name, type_string + "[]", metadata, timestamp)
    
    def append(self, data: List[T], timestamp: int = 0) -> None:
        res = []
        for entry in data:
            if (ds := getattr(self._type, '_WPIStruct', None)):
                ds: 'StructDescriptor'
                ser = ds.pack(data)
            else:
                ser = wpistruct.pack(data)
            res.append(ser)
        ser = b''.join(res)
        self._raw.append(ser, timestamp)
    
    def finish(self, timestamp: int = 0) -> None:
        self._raw.finish(timestamp)
    
    def setMetadata(self, metadata: str, timestamp: int = 0) -> None:
        self._raw.setMetadata(metadata, timestamp)

def add_proto_schema(log: DataLog, proto: 'GeneratedProtocolMessageType', timestamp: int):
    from .protobuf import _iter_descriptor
    if timestamp == 0:
        from ntcore import _now
        timestamp = _now()
    
    for (typeString, schema) in _iter_descriptor(proto.DESCRIPTOR.file, log.hasSchema):
        log.addSchema(typeString, "proto:FileDescriptorProto", schema, timestamp)

class ProtoLogEntry(Generic[T]):
    def __init__(self, log: DataLog, name: str, type: Type[T], metadata: str = '', timestamp: int = 0):
        from .protobuf import _type_str
        add_proto_schema(log, type, timestamp)
        self._type = type
        self._raw = RawLogEntry(log, name, _type_str(type), metadata, timestamp)
    
    def append(self, data: T, timestamp: int = 0) -> None:
        """
        Appends a record to the log.
        
        :param data:      Data to record
        :param timestamp: Time stamp (may be 0 to indicate now)
        """
        ser: bytes = data.SerializeToString()
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


class PyToNtHandler(logging.Handler):
    "Forward Python logs to DataLog"
    def __init__(self, log: DataLog, path: str = 'log', level: 'logging._Level' = 0) -> None:
        super().__init__(level)
        self.entry = StringLogEntry(log, path)
        self.setFormatter(logging.Formatter('[%(levelname)s]%(name)s:%(message)s'))
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.entry.append(msg)
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)
    
    def close(self) -> None:
         self.entry.finish()
         del self.entry

         return super().close()