from typing import Protocol, TypeVar, Generic
from datetime import timedelta
from abc import ABC, abstractmethod
from util.timestamp import Timestamp


class HasTimestamp(Protocol):
	@property
	def ts(self) -> Timestamp: ...


M = TypeVar('M', bound=HasTimestamp)
# S = TypeVar('S', bound=HasTimestamp)

class Filter(ABC, Generic[M]):
	def validate_delta(self, delta: timedelta):
		pass

	def clear(self):
		pass

	@abstractmethod
	def observe(self, measurement: M):
		pass

	@abstractmethod
	def predict(self, now: Timestamp, delta: timedelta):
		pass
	
T = TypeVar('T')
class InterpolableData(Generic[T]):
	def sample(self, timstamp: Timestamp) -> T | None:
		pass