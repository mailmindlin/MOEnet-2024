from typing import Protocol, TypeVar, Generic
from util.timestamp import Timestamp


class HasTimestamp(Protocol):
	ts: Timestamp


S = TypeVar('S', bound=HasTimestamp)

class Filter(Generic[S]):
	pass
	
T = TypeVar('T')
class InterpolableData(Generic[T]):
	def sample(self, timstamp: Timestamp) -> T | None:
		pass