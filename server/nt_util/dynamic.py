from typing import Generic, TypeVar, Callable, Optional, Union, Tuple, List, overload
from .generic import GenericPublisher, GenericSubscriber, GenericTsValue


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
	
	def __enter__(self):
		return self
	
	def __exit__(self, *args):
		self.close()
	
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
	
	@overload
	def get_fresh_ts(self) -> Optional[Tuple[P, int]]:
		if self._handle is None:
			return None
		at = self._handle.getAtomic(None)
		if (at.time != 0) and (at.serverTime != self._fresh_time):
			self._fresh_time = at.serverTime
			return (at.value, at.serverTime)