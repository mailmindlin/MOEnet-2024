from typing import TYPE_CHECKING, TypeVar, Callable, Generic, Protocol, Self, overload, Any
from collections.abc import Hashable, ItemsView
import enum
from dataclasses import dataclass

from util.timestamp import Timestamp
from .types import InterpolableData
from .cascade import Tracked

undefined = object()

if TYPE_CHECKING:
	SK = TypeVar('SK')
	SV = TypeVar('SV')
	class SortedDict(dict[SK, SV]):
		def peekitem(self, idx: int = -1) -> tuple[SK, SV]: ...
		def bisect_right(self, value: SK) -> int: ...
else:
	from sortedcontainers import SortedDict


class Comparable(Protocol):
    def __lt__(self, other: Self, /) -> bool: ...

D = TypeVar('D', bound=Comparable)


class Key(Hashable, Comparable, Protocol[D]):
	"Key type"
	@overload
	def __sub__(self, other: D, /) -> Self: ...
	@overload
	def __sub__(self, other: Self, /) -> D: ...
	def __sub__(self, other: Self | D, /) -> Self | D: ...

K = TypeVar('K', bound=Key)
V = TypeVar('V')
T = TypeVar('T')

class InterpolateResult(Generic[V]):
	@staticmethod
	def wrap(buffer: 'InterpolatingBuffer[K, V, D]', key: K, bottomBound: tuple[K,V] | None, topBound: tuple[K,V] | None):
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
				buffer,
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
	
	def get(self, default: T) -> V | T: ...

class InterpolateEmpty(InterpolateResult[V]):
	"Empty InterpolateResult"
	def get(self, default: T) -> T:
		return default

@dataclass
class InterpolateBefore(InterpolateResult[V]):
	right: V
	def get(self, default: T) -> V:
		return self.right

@dataclass
class InterpolateAfter(InterpolateResult[V]):
	left: V
	def get(self, default: T) -> V:
		return self.left

@dataclass
class InterpolateExact(InterpolateResult[V]):
	value: V
	def get(self, default: T) -> V:
		return self.value

@dataclass
class InterpolateBetween(InterpolateResult[V], Generic[K, V, D]):
	buffer: 'InterpolatingBuffer[K, V, D]'
	left: tuple[K,V]
	right: tuple[K,V]
	p: float

	def get(self, default: T) -> V:
		return self.buffer._lerp(
			self.left[1],
			self.right[1],
			self.p,
		)

class TrackedInterpolation(Tracked[V | T], Generic[K, V, T]):
	"Track a"
	def __init__(self, buffer: 'InterpolatingBuffer[K, V, Any]', key: K, default: T) -> None:
		super().__init__()
		self._buffer = buffer
		self.key = key
		self.default = default
		self._bottom, self._top = self._buffer._get_bounds(self.key)
		self.value = InterpolateResult.wrap(buffer, key, self._bottom, self._top).get(default)
		self._buffer_modcount = self._buffer._modcount
	
	def __repr__(self) -> str:
		return f'TrackedInterpolation(buffer={self._buffer!r}, key={self.key!r}, default={self.default!r})'

	@property
	def is_fresh(self):
		buf_mc = self._buffer._modcount
		if buf_mc == self._buffer_modcount:
			return True
		
		bottom, top = self._buffer._get_bounds(self.key)
		if (bottom != self._bottom) or (top != self._top):
			return False
		# Update this to reduce freshness checks
		self._buffer_modcount = buf_mc
		return True

	def refresh(self):
		buf_mc = self._buffer._modcount
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
				self.value = InterpolateResult.wrap(self._buffer, self.key, bottom, top).get(self.default)
		
		return self


class InterpolatingBuffer(Generic[K, V, D]):
	def __init__(self, historyLength: D, lerp: Callable[[V, V, float], V]):
		self.historyLength = historyLength
		self._snapshots: SortedDict[K, V] = SortedDict()
		self._lerp = lerp
		self._modcount = 0
	
	def _clean_up(self, time: K):
		"Removes samples older than our current history size."
		first = time - self.historyLength
		while len(self._snapshots) > 0:
			entry: tuple[K, V] = self._snapshots.peekitem(0)
			key = entry[0]
			if key < first:
				del self._snapshots[key]
			else:
				break

	def __len__(self):
		return len(self._snapshots)
	
	def clear(self):
		self._snapshots.clear()
		self._modcount += 1
	
	def add(self, key: K, value: V):
		self._clean_up(key)
		self._snapshots[key] = value
		self._modcount += 1
	
	def _get_bounds(self, key: K) -> tuple[tuple[K,V] | None, tuple[K,V] | None]:
		# Special case for when the requested time is the same as a sample
		key_idx = self._snapshots.bisect_right(key)
		if key_idx > 0:
			bottomBound = self._snapshots.peekitem(key_idx - 1)
			bottomKey, _ = bottomBound
			# If an exact match exists, it will be in bottomBound
			if bottomKey == key:
				return bottomBound, bottomBound
		else:
			bottomBound = None
		
		if key_idx >= len(self._snapshots):
			# Index is to the right of any value
			topBound = None
		else:
			topBound = self._snapshots.peekitem(key_idx)
		return bottomBound, topBound
	
	def _get_ex(self, key: K):
		if len(self._snapshots) == 0:
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
		res = self._get_ex(key)
		return res.get(default)
	
	def sample(self, key: K) -> V | None:
		return self.get(key)

	@overload
	def track(self, key: K) -> Tracked[V | None]: ...
	@overload
	def track(self, key: K, default: V) -> Tracked[V]: ...
	@overload
	def track(self, key: K, default: T) -> Tracked[V | T]: ...
	def track(self, key: K, default: T | None = None) -> Tracked[V | T | None]:
		return TrackedInterpolation(self, key, default)
	
	@overload
	def latest(self) -> Tracked[V | None]: ...
	@overload
	def latest(self, default: T) -> Tracked[V | T]: ...
	def latest(self, default: T = None) -> Tracked[V | T]:
		raise NotImplementedError()
		
	def getInternalBuffer(self) -> ItemsView[K, V]:
		return self._snapshots.items()