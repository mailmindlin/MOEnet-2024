from typing import Generic, TypeVar, Callable, Optional, Union, Tuple, List, overload
from .generic import GenericPublisher, GenericSubscriber


P = TypeVar("P", bool, int, float, str, List[bool], List[int], List[float], List[str])
T = TypeVar("T")


class DynamicPublisher(Generic[T]):
	def __init__(self, builder: Callable[[], GenericPublisher[T]]) -> None:
		super().__init__()
		self._builder = builder
		self._handle = None
		self._last = None
	
	@property
	def enabled(self) -> bool:
		return (self._handle is not None)

	@enabled.setter
	def enabled(self, enabled: bool):
		if enabled == (self.enabled):
			return
		elif enabled:
			self._handle = self._builder()
		else:
			self._handle.close()
			self._handle = None
			self._last = None
	
	def close(self):
		self.enabled = False

	def set(self, value: T, time: int = 0):
		if self._handle:
			self._handle.set(value, time)
			self._last = value
	
	def set_fresh(self, value: T):
		if self._last != value:
			self.set(value)
		

class DynamicSubscriber(Generic[P]):
	"NetworkTables subscriber that can easily be enabled/disabled"
	def __init__(self, factory: Callable[[], GenericSubscriber[P]]) -> None:
		super().__init__()
		self._factory = factory
		self._handle = None
		self._fresh_time = None
	
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
	
	def get(self, default: Optional[T] = None) -> Union[P, T]:
		if self._handle is None:
			return default
		else:
			return self._handle.get(default)
	
	@overload
	def get_fresh(self) -> Optional[P]: ...
	@overload
	def get_fresh(self, default: T) -> Union[P, T]: ...
	def get_fresh(self, default: T = None) -> Union[P, T]:
		if self._handle is None:
			return default
		at = self._handle.getAtomic(None)
		if (at.time != 0) and (at.serverTime != self._fresh_time):
			self._fresh_time = at.serverTime
			return at.value
		else:
			return default
	
	@overload
	def get_fresh_ts(self) -> Optional[Tuple[P, int]]:
		if self._handle is None:
			return None
		at = self._handle.getAtomic(None)
		if (at.time != 0) and (at.serverTime != self._fresh_time):
			self._fresh_time = at.serverTime
			return (at.value, at.serverTime)