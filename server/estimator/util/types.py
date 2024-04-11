from typing import Protocol
from datetime import timedelta
from abc import ABC, abstractmethod
from util.timestamp import Timestamp


class HasTimestamp(Protocol):
	@property
	def ts(self) -> Timestamp: ...


class Filter[M: HasTimestamp](ABC):
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
	

class InterpolableData[T]:
	def sample(self, timstamp: Timestamp) -> T | None:
		pass