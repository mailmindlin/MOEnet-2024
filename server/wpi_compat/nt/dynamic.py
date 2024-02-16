from typing import overload, Generic, TypeVar, Callable, Optional, Union, Tuple, Type
import typing
from .typedef import GenericPublisher, GenericSubscriber, GenericTsValue, GenericTopic
from ntcore import NetworkTableInstance, NetworkTable, PubSubOptions
import numpy as np


P = TypeVar("P", bool, int, float, str, list[bool], list[int], list[float], list[str])
T = TypeVar("T")

def _make_topic(base: Union[NetworkTableInstance, NetworkTable], path: str, type: Type[T]) -> GenericTopic[T]:
	# Check scalar types
	if type == bool:
		return base.getBooleanTopic(path)
	if type == int:
		return base.getIntegerTopic(path)
	if type == str:
		return base.getStringTopic(path)
	if type in (float, np.float_, np.float64):
		return base.getDoubleTopic(path)
	if type == np.float32:
		return base.getFloatTopic(path)
	
	# Struct types
	from ..struct import get_descriptor
	try:
		get_descriptor(type)
	except TypeError:
		pass
	else:
		return base.getStructTopic(path, type)
	#TODO: protobuf
	
	if origin := typing.get_origin(type):
		args = typing.get_args(type)
		if origin in (list, typing.List):
			if len(args) == 0:
				raise TypeError(f'Unable to map generic list to NetworkTables topic')
			if len(args) > 1:
				raise TypeError(f'Too many arguments for list type')
			
			t0 = args[0]
			if t0 == bool:
				return base.getBooleanArrayTopic(path)
			if t0 == int:
				return base.getIntegerArrayTopic(path)
			if t0 == str:
				return base.getStringArrayTopic(path)
			if t0 in (float, np.float_, np.float64):
				return base.getDoubleArrayTopic(path)
			if t0 == np.float32:
				return base.getFloatArrayTopic(path)
			try:
				get_descriptor(t0)
			except TypeError:
				pass
			else:
				return base.getStructArrayTopic(path, t0)
			#TODO: protobuf
	raise TypeError(f'Unable to map type {type} to NetworkTables topic')
		
			
	
class DynamicPublisher(Generic[T]):
	@classmethod
	def create(cls, base: Union[NetworkTableInstance, NetworkTable], path: str, type: Type[T], options: Optional[PubSubOptions] = None) -> 'DynamicPublisher[T]':
		topic = _make_topic(base, path, type)
		return cls(topic, options)

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
		

class DynamicSubscriber(Generic[P]):
	"NetworkTables subscriber that can easily be enabled/disabled"

	@classmethod
	def create(cls, base: Union[NetworkTableInstance, NetworkTable], path: str, type: Type[T], defaultValue: T, options: Optional[PubSubOptions] = None, enabled: bool = False) -> 'DynamicSubscriber[T]':
		topic = _make_topic(base, path, type)
		return cls(topic, defaultValue, options, enabled=enabled)
	
	@classmethod
	def create_struct(cls, base: Union[NetworkTableInstance, NetworkTable], path: str, type: Type[T], defaultValue: T, options: Optional[PubSubOptions] = None) -> 'DynamicSubscriber[T]':
		pass
	
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

	def readQueue(self) -> list[GenericTsValue[P]]:
		self._pull_queue()
		res = self._read_queue
		self._read_queue.clear()
		if self._read_queue_truncated:
			import warnings
			warnings.warn(f"read queue for NT topic {self._topic.getName()} was truncated", RuntimeWarning)
		return res
	
	def getAtomic(self) -> Optional[GenericTsValue[P]]:
		if self._raw_subscriber is None:
			return None
		else:
			res = self._raw_subscriber.getAtomic()
			if res.time == 0:
				# No data
				return None
			return res
	
	@overload
	def get(self) -> Optional[P]: ...
	@overload
	def get(self, default: T) -> Union[P, T]: ...
	def get(self, default: Optional[T] = None):
		if v := self.getAtomic():
			return v.value
		else:
			return default
	
	@overload
	def get_fresh(self) -> Optional[P]: ...
	@overload
	def get_fresh(self, default: T) -> Union[P, T]: ...
	def get_fresh(self, default: Optional[T] = None) -> Union[P, T, None]:
		"Get a value, but only if it's new"
		if (v := self.get_fresh_ts()) is not None:
			return v.value
		else:
			return default
	
	def get_fresh_ts(self) -> Optional[GenericTsValue[P]]:
		"Like [get_fresh], but returns a timestamp too"
		self._pull_queue() # update _fresh_data
		res = self._fresh_data
		if res is not None:
			self._fresh_data = None
			return res
		return None