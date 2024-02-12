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
	def create(cls, base: Union[NetworkTableInstance, NetworkTable], path: str, type: Type[T], defaultValue: T, options: Optional[PubSubOptions] = None) -> 'DynamicSubscriber[T]':
		topic = _make_topic(base, path, type)
		return cls(topic, defaultValue, options)
	
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
		self._fresh_time = None
		"Track last fresh timestamp for [get_fresh]"

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
		
		self._fresh_time = None
	
	close = stop
	
	def getAtomic(self) -> Optional[GenericTsValue[P]]:
		if self._raw_subscriber is None:
			return None
		else:
			res = self._raw_subscriber.getAtomic()
			if res.time == 0:
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
	def get_fresh(self, default: Optional[T] = None) -> Union[P, T]:
		"Get a value, but only if it's new"
		if v := self.getAtomic():
			if v.serverTime != self._fresh_time:
				self._fresh_time = v.serverTime
				return v.value
		return default
	
	def get_fresh_ts(self) -> Optional[Tuple[P, int]]:
		"Like [get_fresh], but returns a timestamp too"
		if v := self.getAtomic():
			if v.serverTime != self._fresh_time:
				self._fresh_time = v.serverTime
				return (v.value, v.time)
		return None