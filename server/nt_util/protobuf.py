from typing import TYPE_CHECKING, Generic, Type, TypeVar, Union, Callable, Iterable, Tuple, overload
from ntcore import NetworkTableInstance, NetworkTable, PubSubOptions, RawTopic, RawPublisher, RawSubscriber
from dataclasses import dataclass

from .generic import GenericPublisher, GenericSubscriber, GenericEntry, GenericTsValue

if TYPE_CHECKING:
	from google.protobuf.pyext.cpp_message import GeneratedProtocolMessageType
	from google.protobuf.descriptor import FileDescriptor

T = TypeVar("T")

def _type_str(proto: 'GeneratedProtocolMessageType') -> str:
	if name := getattr(proto, 'type_string', None):
		return name
	return 'proto:' + proto.DESCRIPTOR.name

def _iter_descriptor(file: 'FileDescriptor', exists: Callable[[str], bool]) -> Iterable[Tuple[str, bytes]]:
	"Iterate (recursively) through FileDescriptor schemas"
	name = "proto:" + file.name #TODO: is this file.package + file.name?
	if exists(name):
		return
	for dep in file.dependencies:
		yield from _iter_descriptor(dep, exists)
	yield (name, file.serialized_pb)
	
def add_schema(nt: NetworkTableInstance, proto: 'GeneratedProtocolMessageType'):
	"Register a protobuf's schema with NetworkTables"
	
	for (typeString, schema) in _iter_descriptor(proto.DESCRIPTOR.file, nt.hasSchema):
		nt.addSchema(typeString, "proto:FileDescriptorProto", schema)


class ProtobufPublisher(Generic[T]):
	def __init__(self, proto: Type[T], publisher: RawPublisher) -> None:
		super().__init__()
		self._proto = proto
		self._publisher = publisher
	
	def close(self):
		self._publisher.close()
		del self._publisher
	# def getTopic(self) -> 'ProtoTopic[P]': ...
	def set(self, value: T, time: int = 0):
		b: bytes = value.SerializeToString()
		self._publisher.set(b, time)
	def setDefault(self, value: T):
		b: bytes = value.SerializeToString()
		self._publisher.set(b)

@dataclass
class TimestampedProto(GenericTsValue[T]):
	serverTime: int
	time: int
	value: T


undefined = object()
class ProtobufSubscriber(Generic[T]):
	def __init__(self, proto: Type[T], subscriber: RawSubscriber, defaultValue: T) -> None:
		super().__init__()
		self._proto = proto
		self._subscriber = subscriber
		self._default_value = defaultValue
	
	def __enter__(self) -> 'ProtobufSubscriber[T]':
		return self
	def __exit__(self, *args):
		self.close()
	
	def close(self):
		self._subscriber.close()
		del self._subscriber
	
	def _get_raw(self, value: bytes, defaultValue: T = undefined) -> T:
		if len(value) == 0:
			if defaultValue is undefined:
				return self._default_value
			else:
				return defaultValue
		
		#TODO: swallow errors
		return self._proto.ParseFromString(value)
	
	@overload
	def get(self) -> T: ...
	@overload
	def get(self, defaultValue: T = undefined) -> T:
		b = self._subscriber.get()
		return self._get_raw(b, defaultValue)

	@overload
	def getAtomic(self) -> GenericTsValue[T]: ...
	@overload
	def getAtomic(self, defaultValue: T = undefined) -> GenericTsValue[T]:
		a = self._subscriber.getAtomic()
		value = self._get_raw(a.value, defaultValue)
		return TimestampedProto(a.serverTime, a.time, value)


_default_pso = PubSubOptions()
class ProtobufTopic(Generic[T]):
	@staticmethod
	def wrap(root: Union[NetworkTableInstance, NetworkTable], name: str, proto: Type[T]) -> 'ProtobufTopic[T]':
		topic = root.getRawTopic(name)
		return ProtobufTopic(topic, proto)

	def __init__(self, topic: RawTopic, proto: Type[T]):
		self._topic = topic
		self._proto = proto
	
	def close(self) -> None:
		self._topic.close()
	
	def getEntry(self, defaultValue: T, options: PubSubOptions = _default_pso) -> GenericEntry[T]: 
		...
	def getEntryEx(self, typeString: str, defaultValue: T, options: PubSubOptions = _default_pso) -> GenericEntry[T]: 
		...
	def publish(self, options: PubSubOptions = _default_pso) -> GenericPublisher[T]: 
		add_schema(self._topic.getInstance(), self._proto)
		return ProtobufPublisher(
			self._proto,
			self._topic.publish(_type_str(self._proto), options)
		)
	def subscribe(self, defaultValue: T, options: PubSubOptions = _default_pso) -> GenericSubscriber[T]:
		return ProtobufSubscriber(
			self._proto,
			self._topic.subscribe(_type_str(self._proto), bytes(), options),
			defaultValue,
		)
	def subscribeEx(self, typeString: str, defaultValue: T, options: PubSubOptions = _default_pso) -> GenericSubscriber[T]: 
		...