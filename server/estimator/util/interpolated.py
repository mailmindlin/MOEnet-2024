from typing import TYPE_CHECKING, Callable, Protocol, Self, overload, Reversible
from collections.abc import Hashable, Sequence
from dataclasses import dataclass

from .cascade import Tracked

undefined = object()

if TYPE_CHECKING:
	class SortedDict[SK, SV](dict[SK, SV]):
		def peekitem(self, idx: int = -1) -> tuple[SK, SV]: ...
		def bisect_right(self, value: SK) -> int: ...
else:
	from sortedcontainers import SortedDict


class Comparable(Protocol):
	def __lt__(self, other: Self, /) -> bool: ...

class Delta(Comparable, Protocol):
	def __truediv__(self, other: Self, /) -> float: ...

class Key[D: Delta](Hashable, Comparable, Protocol):
	"Key type"
	# @overload
	# def __sub__(self, delta: D, /) -> Self: ...
	# @overload
	def __sub__(self, other: Self, /) -> D: ...

class InterpolateResult[V]:
	@staticmethod
	def wrap[K: Key](view: 'InterpolatingView[K, V]', key: K, bottomBound: tuple[K,V] | None, topBound: tuple[K,V] | None):
		# Return null if neither sample exists, and the opposite bound if the other is null
		if (topBound is not None) and (bottomBound is not None):
			if topBound[0] == key:
				return InterpolateExact(topBound[1])
			if bottomBound[0] == key:
				# For completeness, not that I think this branch will be taken
				return InterpolateExact(bottomBound[1])

			# Otherwise, interpolate. Because T is between [0, 1], we want the ratio of (the difference
			# between the current time and bottom bound) and (the difference between top and bottom
			# bounds).
			
			p: float = (key - bottomBound[0]) / (topBound[0] - bottomBound[0])
			return InterpolateBetween(
				view,
				bottomBound,
				topBound,
				p,
			)
		elif topBound is not None:
			return InterpolateBefore(topBound[1])
		elif bottomBound is not None:
			return InterpolateAfter(bottomBound[1])
		else:
			# No bounds
			return InterpolateEmpty()
	
	def get[T](self, default: T) -> V | T: ...

class InterpolateEmpty[V](InterpolateResult[V]):
	"Empty InterpolateResult"
	def get[T](self, default: T) -> T:
		return default

@dataclass
class InterpolateBefore[V](InterpolateResult[V]):
	right: V
	def get[T](self, default: T) -> V | T:
		return self.right

@dataclass
class InterpolateAfter[V](InterpolateResult[V]):
	left: V
	def get[T](self, default: T) -> V | T:
		return self.left

@dataclass
class InterpolateExact[V](InterpolateResult[V]):
	value: V
	def get[T](self, default: T) -> V | T:
		return self.value

@dataclass
class InterpolateBetween[K: Key, V](InterpolateResult[V]):
	buffer: 'InterpolatingView[K, V]'
	left: tuple[K,V]
	right: tuple[K,V]
	p: float

	def get[T](self, default: T) -> V | T:
		return self.buffer._lerp(
			self.left[1],
			self.right[1],
			self.p,
		)

class TrackedInterpolation[K: Key, V, T](Tracked[V | T]):
	"Track a"
	def __init__(self, buffer: 'InterpolatingView[K, V]', key: K, default: T) -> None:
		super().__init__()
		self._buffer = buffer
		self.key = key
		self.default = default
		self._bottom, self._top = self._buffer._get_bounds(self.key)
		self._value = InterpolateResult.wrap(buffer, key, self._bottom, self._top).get(default)
		self._buffer_modcount = self._buffer.modcount
	
	@property
	def current(self):
		return self._value
	
	def __repr__(self) -> str:
		return f'TrackedInterpolation(buffer={self._buffer!r}, key={self.key!r}, default={self.default!r})'

	@property
	def is_fresh(self):
		buf_mc = self._buffer.modcount
		if buf_mc == self._buffer_modcount:
			return True
		
		bottom, top = self._buffer._get_bounds(self.key)
		if (bottom != self._bottom) or (top != self._top):
			return False
		# Update this to reduce freshness checks
		self._buffer_modcount = buf_mc
		return True

	def refresh(self):
		buf_mc = self._buffer.modcount
		if buf_mc == self._buffer_modcount:
			# Fresh
			return self

		bottom, top = self._buffer._get_bounds(self.key)
		if (top != self._top) or (bottom != self._bottom):
			if (self._top is not None) and (self._bottom is not None) and ((top is None) or (bottom is None)):
				# Going from lerp -> edge is worse, don't do it
				pass
			else:
				self._top = top
				self._bottom = bottom
				self._value = InterpolateResult.wrap(self._buffer, self.key, bottom, top).get(self.default)
		
		return self

class SequenceQueue[K: Key, V](Protocol):
	def __len__(self) -> int: ...
	def bisect_right(self, key: K, /) -> int: ...
	def peekitem(self, index: int, /) -> tuple[K, V]: ...
	def keys(self) -> Reversible[K]: ...
	def items(self) -> Reversible[tuple[K, V]]: ...

class SortedSequenceAdapter[K: Key, V](SequenceQueue[K, V]):
	def __init__(self, backing: Sequence[V], keyfunc: Callable[[V], K]):
		self.backing = backing
		self._keyfunc = keyfunc
	def __len__(self):
		return len(self.backing)
	def bisect_right(self, key: K) -> int:
		from bisect import bisect_right
		return bisect_right(self.backing, key, key=self._keyfunc)
	def peekitem(self, index: int) -> tuple[K, V]:
		v = self.backing[index]
		k = self._keyfunc(v)
		return (k, v)
	def keys(self) -> Reversible[K]:
		raise NotImplementedError()
	def items(self) -> Reversible[tuple[K, V]]:
		raise NotImplementedError()


class InterpolatingView[K: Key, V]:
	def __init__(self, queue: SequenceQueue[K, V], lerp: Callable[[V, V, float], V]) -> None:
		self._queue = queue
		self._lerp = lerp
		self.modcount = 0
		"Count modifications, for `Tracked` caching"
	
	def __len__(self):
		return len(self._queue)
	
	def _get_bounds(self, key: K) -> tuple[tuple[K,V] | None, tuple[K,V] | None]:
		# Special case for when the requested time is the same as a sample
		key_idx = self._queue.bisect_right(key)
		if key_idx > 0:
			bottomBound = self._queue.peekitem(key_idx - 1)
			bottomKey, _ = bottomBound
			# If an exact match exists, it will be in bottomBound
			if bottomKey == key:
				return bottomBound, bottomBound
		else:
			bottomBound = None
		
		if key_idx >= len(self._queue):
			# Index is to the right of any value
			topBound = None
		else:
			topBound = self._queue.peekitem(key_idx)
		return bottomBound, topBound
	
	def _get_ex(self, key: K):
		if len(self._queue) == 0:
			return InterpolateEmpty()
		bottomBound, topBound = self._get_bounds(key)

		if (topBound is not None) and topBound[0] == key:
			# Exact match
			return InterpolateExact(topBound[1])
		
		return InterpolateResult.wrap(self, key, bottomBound, topBound)
	
	@overload
	def get(self, /, key: K) -> V | None: ...
	@overload
	def get(self, /, key: K, default: V) -> V: ...
	def get(self, /, key: K, default: V | None = None) -> V | None:
		"Get (interpolated) value for timestamp"
		res = self._get_ex(key)
		return res.get(default)
	
	def sample(self, key: K) -> V | None:
		"Get (interpolated) value for timestamp"
		return self.get(key)

	@overload
	def track(self, key: K) -> Tracked[V | None]: ...
	@overload
	def track(self, key: K, default: V) -> Tracked[V]: ...
	@overload
	def track[T](self, key: K, default: T) -> Tracked[V | T]: ...
	def track[T](self, key: K, default: T = None) -> Tracked[V | T | None]:
		return TrackedInterpolation(self, key, default)
	
	@overload
	def latest(self) -> Tracked[V | None]: ...
	@overload
	def latest[T](self, default: T) -> Tracked[V | T]: ...
	def latest[T](self, default: T = None) -> Tracked[V | T]:
		raise NotImplementedError()
		
	def keys(self):
		return self._queue.keys()
	
	def items(self):
		return self._queue.items()

class InterpolatingBuffer[K: Key, V, D: Comparable](InterpolatingView[K, V]):
	_queue: SortedDict[K, V]
	def __init__(self, historyLength: D, lerp: Callable[[V, V, float], V]):
		super().__init__(SortedDict(), lerp)
		self.historyLength = historyLength
	
	def _clean_up(self, last_key: K):
		"Removes samples older than our current history size."
		first = last_key - self.historyLength
		while len(self._queue) > 0:
			entry: tuple[K, V] = self._queue.peekitem(0)
			key = entry[0]
			if key < first:
				del self._queue[key]
			else:
				break

	def clear(self):
		self._queue.clear()
		self.modcount += 1
	
	def add(self, key: K, value: V):
		self._clean_up(key)
		self._queue[key] = value
		self.modcount += 1
