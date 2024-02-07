from typing import overload, Generic, TypeVar, Callable, Optional, Union, Tuple, Type
from .typedef import GenericPublisher, GenericSubscriber, GenericTsValue, GenericTopic
from ntcore import NetworkTableInstance, NetworkTable, PubSubOptions


P = TypeVar("P", bool, int, float, str, list[bool], list[int], list[float], list[str])
T = TypeVar("T")


class DynamicPublisher(Generic[T]):
	@staticmethod
	def create(base: Union[NetworkTableInstance, NetworkTable], path: str, type: Type[T], options: Optional[PubSubOptions] = None) -> 'DynamicPublisher[T]':
		pass

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
			self._start()

	def _start(self):
		if self._topic is None:
			self._topic = self._builder()
		
		self._publisher = self._topic.publish(self._options)
	
	def _stop(self):
		if self._publisher is not None:
			self._publisher.close()
			self._publisher = None
		
		if (self._topic is not None) and (self._builder is not None):
			# Close topic if we can re-create it
			self._topic.close()
			self._topic = None
		
		self._last = None
	
	@property
	def enabled(self) -> bool:
		return (self._publisher is not None)

	@enabled.setter
	def enabled(self, enabled: bool):
		if enabled == (self.enabled):
			return
		elif enabled:
			self._start()
		else:
			self.close()
	
	def __enter__(self):
		"Context manager that closes on exit"
		return self
	
	def __exit__(self, *args):
		self._stop()
	
	def close(self):
		self._stop()

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
	def __init__(self, factory: Callable[[], GenericSubscriber[P]]) -> None:
		super().__init__()
		self._factory = factory
		self._handle = None
		self._fresh_time = None
	
	def __enter__(self):
		return self
	
	def __exit__(self, *args):
		self.close()
	
	@property
	def enabled(self) -> bool:
		return (self._handle is not None)

	@enabled.setter
	def enabled(self, enabled: bool):
		if enabled == (self.enabled):
			return
		elif enabled:
			self._handle = self._factory()
		else:
			self._handle.close()
			self._handle = None
			self._fresh_time = None
	
	def close(self):
		self.enabled = False
	
	def getAtomic(self) -> Optional[GenericTsValue[P]]:
		if self._handle is None:
			return None
		else:
			res = self._handle.getAtomic()
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
	def get_fresh(self, default: T = None) -> Union[P, T]:
		if v := self.getAtomic():
			if v.serverTime != self._fresh_time:
				self._fresh_time = v.serverTime
				return v.value
		return default
	
	def get_fresh_ts(self) -> Optional[Tuple[P, int]]:
		if v := self.getAtomic():
			if v.serverTime != self._fresh_time:
				self._fresh_time = v.serverTime
				return (v.value, v.time)
		return None