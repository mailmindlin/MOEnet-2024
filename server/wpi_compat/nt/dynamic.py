from typing import overload, Generic, TypeVar, Callable, Optional, Union, Type, Literal
import typing

from wpiutil import wpistruct
import numpy as np
from ntcore import NetworkTableInstance, NetworkTable, PubSubOptions

from .typedef import GenericPublisher, GenericTsValue, GenericTopic


P = TypeVar("P", bool, int, float, str, list[bool], list[int], list[float], list[str])
T = TypeVar("T")
D = TypeVar("D")

NetworkTableLike = Union[NetworkTableInstance, NetworkTable]

def _topic_f64(nt: NetworkTableLike, path: str):
	return nt.getDoubleTopic(path)
def _topic_list_f64(nt: NetworkTableLike, path: str):
	return nt.getDoubleArrayTopic(path)

TopicFactory = Callable[[NetworkTableLike, str], GenericTopic]
SCALAR_FACTORIES: dict[type, TopicFactory] = {
	bool: lambda nt, path: nt.getBooleanTopic(path),
	int: lambda nt, path: nt.getIntegerTopic(path),
	np.float32: lambda nt, path: nt.getFloatTopic(path),
	str: lambda nt, path: nt.getStringTopic(path),
	# A bunch of aliases for double
	float: _topic_f64,
	np.float_: _topic_f64,
	np.float64: _topic_f64,
	wpistruct.double: _topic_f64,
}
ARRAY_FACTORIES: dict[type, Callable[[NetworkTableLike, str], GenericTopic]] = {
	bool: lambda nt, path: nt.getBooleanArray(path),
	int: lambda nt, path: nt.getIntegerArrayTopic(path),
	np.float32: lambda nt, path: nt.getFloatArrayTopic(path),
	str: lambda nt, path: nt.getStringArrayTopic(path),
	# A bunch of aliases for double
	float: _topic_list_f64,
	np.float_: _topic_list_f64,
	np.float64: _topic_list_f64,
	wpistruct.double: _topic_list_f64,
}

def _topic_factory(type: Type[T], mode: Literal['scalar', 'struct', 'proto', None] = None) -> Callable[[NetworkTableLike, str], GenericTopic[T]]:
	# Check scalar types
	excs = []
	if mode in ('scalar', None):
		try:
			return SCALAR_FACTORIES[type]
		except KeyError as e:
			excs.append(('Not a scalar', e))
	
	if mode in ('struct', None):
		# Struct types
		from ..struct import get_descriptor
		try:
			get_descriptor(type)
		except TypeError as e:
			excs.append(('Not a struct', e))
		else:
			return lambda nt, path: nt.getStructTopic(path, type)
	
	# Protobuf types
	if mode in ('proto', None):
		from ..protobuf import is_protobuf_type
		if is_protobuf_type(type):
			from .protobuf import ProtobufTopic
			return lambda nt, path: ProtobufTopic.wrap(nt, path, type)
		else:
			excs.append(('Not a protobuf', None))
	
	# Array types
	if origin := typing.get_origin(type):
		args = typing.get_args(type)
		if origin in (list, typing.List):
			if len(args) == 0:
				raise TypeError(f'Unable to map generic list to NetworkTables topic')
			if len(args) > 1:
				raise TypeError(f'Too many arguments for list type')
			t0 = args[0]
			if mode in ('scalar', None):
				try:
					return ARRAY_FACTORIES[t0]
				except KeyError as e:
					excs.append(('Not a simple array', e))
			if mode in ('struct', None):
				try:
					from ..struct import get_descriptor
					get_descriptor(t0)
				except TypeError as e:
					excs.append(('Not a struct array', e))
				else:
					return lambda nt, path: nt.getStructArrayTopic(path, t0)
			
			#TODO: protobuf arrays
	
	exc = TypeError(f'Unable to map type {type} to NetworkTables topic')
	for msg, e in excs:
		if e is not None:
			msg += f' ({e})'
		exc.add_note(msg)
	raise exc


def _make_topic_factory(base: Union[NetworkTableLike, Callable[[], NetworkTableLike]], path: str, type: Type[T], mode: Literal['scalar', 'struct', 'proto', None] = None) -> Union[GenericTopic[T], Callable[[], GenericTopic[T]]]:
	factory = _topic_factory(type, mode=mode)
	if isinstance(base, (NetworkTableInstance, NetworkTable)):
		return factory(base, path)
	else:
		assert callable(base)
		return lambda: factory(base(), path)
	
class DynamicPublisher(Generic[T]):
	@classmethod
	def create(cls, base: Union[NetworkTableLike, Callable[[], NetworkTableLike]], path: str, type: Type[T], options: Optional[PubSubOptions] = None, *, enabled: bool = False, mode: Literal['scalar', 'struct', 'proto', None] = None) -> 'DynamicPublisher[T]':
		topic = _make_topic_factory(base, path, type, mode=mode)
		return cls(topic, options, enabled=enabled)


	_builder: Optional[Callable[[], GenericTopic[T]]]
	"Topic builder (lets us be lazy)"
	_topic: Optional[GenericTopic[T]]
	"Handle to real topic"
	_options: PubSubOptions
	"Options to use when publishing"
	_publisher: Optional[GenericPublisher[T]]
	"Real publisher handle"
	_last: Optional[T]

	def __init__(self, topic: Union[Callable[[], GenericTopic[T]], GenericTopic[T]], options: Optional[PubSubOptions] = None, *, enabled: bool = False):
		super().__init__()
		if callable(topic):
			self._builder = topic
			self._topic = None
		else:
			self._builder = None
			self._topic = topic
		self._options = options or PubSubOptions()
		self._publisher = None
		self._last = None

		# Enable on start?
		if enabled:
			self.start()

	def start(self):
		"Start publishing"
		# Build topic
		if self._topic is None:
			assert self._builder is not None
			self._topic = self._builder()
		
		self._publisher = self._topic.publish(self._options)
	
	def stop(self):
		"Stop publishing to NetworkTables"
		# Close publisher
		if self._publisher is not None:
			self._publisher.close()
			self._publisher = None
		
		# Close topic if we can rebuild it
		if (self._topic is not None) and (self._builder is not None):
			# Close topic if we can re-create it
			self._topic.close()
			self._topic = None
		
		self._last = None
	
	close = stop
	
	@property
	def enabled(self) -> bool:
		"Is this publisher currently publishing?"
		return (self._publisher is not None)

	@enabled.setter
	def enabled(self, enabled: bool):
		"Is this publisher enabled?"
		if enabled == (self.enabled):
			return
		
		if enabled:
			self.start()
		else:
			self.stop()
	
	def __bool__(self):
		return self.enabled
	
	def __enter__(self):
		"Context manager that closes on exit"
		return self
	
	def __exit__(self, *args):
		self.stop()

	def set(self, value: T, time: int = 0):
		if self._publisher:
			self._publisher.set(value, time)
			self._last = value
	
	def set_fresh(self, value: T):
		"Set, but only if the value is new"
		if self._last != value:
			self.set(value)
		

class DynamicSubscriber(Generic[T]):
	"NetworkTables subscriber that can easily be enabled/disabled"

	@classmethod
	def create(cls, base: Union[NetworkTableLike, Callable[[], NetworkTableLike]], path: str, type: Type[T], defaultValue: T, options: Optional[PubSubOptions] = None, *, enabled: bool = False, mode: Literal['scalar', 'struct', 'proto', None] = None) -> 'DynamicSubscriber[T]':
		topic = _make_topic_factory(base, path, type, mode=mode)
		return cls(topic, defaultValue, options, enabled=enabled)
	
	def __init__(self, topic: Union[Callable[[], GenericTopic[T]], GenericTopic[T]], defaultValue: T, options: Optional[PubSubOptions] = None, *, enabled: bool = False):
		super().__init__()
		if callable(topic):
			self._builder = topic
			self._topic = None
		else:
			self._builder = None
			self._topic = topic
		self._default_value = defaultValue
		"Default value for subscriber"
		self._options = options or PubSubOptions()
		"Options to use when subscribing"
		self._raw_subscriber = None
		"Handle to real subscriber"
		self._read_queue: list[GenericTsValue[T]] = list()
		self._read_queue_truncated = False
		self._fresh_data: Optional[GenericTsValue[T]] = None

		# Enable on start?
		if enabled:
			self.start()
	
	def __enter__(self):
		return self
	
	def __exit__(self, *args):
		self.stop()
	
	@property
	def enabled(self) -> bool:
		return (self._raw_subscriber is not None)

	@enabled.setter
	def enabled(self, enabled: bool):
		if enabled == (self.enabled):
			return
		
		if enabled:
			self.start()
		else:
			self.stop()
	
	def start(self):
		"Start subscribing"
		# Build topic
		if self._topic is None:
			assert self._builder is not None
			self._topic = self._builder()
		
		assert self._raw_subscriber is None
		self._raw_subscriber = self._topic.subscribe(self._default_value, self._options)
	
	def stop(self):
		"Stop subscribing"
		# Close subscriber
		if self._raw_subscriber is not None:
			self._raw_subscriber.close()
			self._raw_subscriber = None
		
		# Close topic if we can rebuild it
		if (self._topic is not None) and (self._builder is not None):
			# Close topic if we can re-create it
			self._topic.close()
			self._topic = None
		
		self._read_queue.clear()
		self._fresh_data = None
	
	close = stop

	def _pull_queue(self):
		if self._raw_subscriber is None:
			return
		# Cap queue cache length
		if len(self._read_queue) > 256:
			self._read_queue = self._read_queue[-256:]
			self._read_queue_truncated = True
		qv = self._raw_subscriber.readQueue()
		self._read_queue.extend(qv)
		if len(qv) > 0:
			self._fresh_data = qv[-1]

	def readQueue(self) -> list[GenericTsValue[T]]:
		self._pull_queue()
		res = self._read_queue
		self._read_queue.clear()
		if self._read_queue_truncated:
			import warnings
			warnings.warn(f"read queue for NT topic {self._topic.getName()} was truncated", RuntimeWarning)
		return res
	
	def getAtomic(self) -> Optional[GenericTsValue[T]]:
		if self._raw_subscriber is None:
			return None
		else:
			res = self._raw_subscriber.getAtomic()
			if res.time == 0:
				# No data
				return None
			return res
	
	@overload
	def get(self) -> Optional[T]: ...
	@overload
	def get(self, default: D) -> Union[D, T]: ...
	def get(self, default: Optional[D] = None):
		if v := self.getAtomic():
			return v.value
		else:
			return default
	
	@overload
	def get_fresh(self) -> Optional[T]: ...
	@overload
	def get_fresh(self, default: D) -> Union[D, T]: ...
	def get_fresh(self, default: Optional[D] = None) -> Union[D, T, None]:
		"Get a value, but only if it's new"
		if (v := self.get_fresh_ts()) is not None:
			return v.value
		else:
			return default
	
	def get_fresh_ts(self) -> Optional[GenericTsValue[T]]:
		"Like [get_fresh], but returns a timestamp too"
		self._pull_queue() # update _fresh_data
		res = self._fresh_data
		if res is not None:
			self._fresh_data = None
			return res
		return None