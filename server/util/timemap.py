from typing import TYPE_CHECKING, Sequence, Optional, TypeVar, Union
from abc import ABC, abstractmethod
from functools import cached_property
import operator, contextvars

from .decorators import classproperty

if TYPE_CHECKING:
	from .clock import Clock, OffsetClock
	from .timestamp import Timestamp

class TimeMapper(ABC):
	"Identity time mapper"
	clock_a: 'Clock'
	clock_b: 'Clock'
	_cm_map: Optional['TimeMap']

	def __init__(self, clock_a: 'Clock', clock_b: 'Clock') -> None:
		super().__init__()
		self.clock_a = clock_a
		self.clock_b = clock_b
	
	def __enter__(self):
		self._cm_map = TimeMap(TimeMap.default, self)
		self._cm_map.__enter__()
		return self

	def __exit__(self, *args):
		assert self._cm_map is not None
		self._cm_map.__exit__()
		del self._cm_map

	@abstractmethod
	def get_offset(self) -> int:
		"Offset, roughtly (b - a)"
		pass

	@property
	def constant_offset(self) -> bool:
		"Is `get_offset` constant?"
		return False

	@property
	def conversion_cost(self) -> int:
		"The cost of applying this map (for looking up in [TimeMap]). Must be non-negative integer."
		return 10
	
	def a_to_b(self, ts_a: 'Timestamp') -> 'Timestamp':
		ts_a.assert_src(self.clock_a)
		return ts_a.offset_ns(self.get_offset(), clock=self.clock_b)
	
	def b_to_a(self, ts_b: 'Timestamp') -> 'Timestamp':
		ts_b.assert_src(self.clock_b)
		return ts_b.offset_ns(-self.get_offset(), clock=self.clock_a)
	
	def __neg__(self) -> 'TimeMapper':
		"Invert"
		return InverseTimeMapper(self)
	
	def __shr__(self, rhs: 'TimeMapper') -> 'ChainedTimeMapper':
		"Chain TimeMappers"
		if isinstance(rhs, TimeMapper):
			assert self.clock_b == rhs.clock_a
			return ChainedTimeMapper([self, rhs])
		return NotImplemented


M = TypeVar('M', bound=TimeMapper)
class TimeMap:
	@classproperty
	def default(cls) -> 'TimeMap':
		return MAP_CTX.get()

	def __init__(self, *mappers: Union['TimeMap', TimeMapper]):
		self._prev_t = None
		self.conversions: dict['Clock', dict['Clock', tuple[TimeMapper, bool]]] = dict()
		for mapper in mappers:
			if isinstance(mapper, TimeMap):
				# Inherit mappings
				for src, prev_src in mapper.conversions.items():
					loc_src = self.conversions.setdefault(src, dict())
					for dst, to_dst in prev_src.items():
						loc_src[dst] = to_dst
			else:
				self.register(mapper, replace=True, is_caching=False)
	
	def __enter__(self):
		self._prev_t = MAP_CTX.set(self)
		return self

	def __exit__(self, *args):
		assert self._prev_t is not None
		MAP_CTX.reset(self._prev_t)
		del self._prev_t
	
	def cached(self, mapper: M) -> M:
		self.register(mapper, False, True)
		return mapper

	def register(self, mapper: TimeMapper, replace: bool = True, is_caching: bool = False) -> bool:
		from_a = self.conversions.setdefault(mapper.clock_a, dict())
		prev_a = from_a.get(mapper.clock_b, None)
		did_replace = False
		if replace or (prev_a is None) or (prev_a[1] and not is_caching):
			from_a[mapper.clock_b] = (mapper, is_caching)
			did_replace = True
		
		# Skip for identity maps
		if mapper.clock_a == mapper.clock_b:
			return did_replace
		
		# Insert replaced
		from_b = self.conversions.setdefault(mapper.clock_b, dict())
		prev_b = from_b.get(mapper.clock_a, None)
		# We are more selective, because this is always 'cached'
		if (prev_b is None) or (prev_b[1] and (replace or (did_replace and prev_b[0] == -prev_a[0]))):
			from_b[mapper.clock_a] = (-mapper, True)
		return did_replace
	
	def get_direct(self, src: 'Clock', dst: 'Clock') -> Optional[TimeMapper]:
		# Try forwards
		if from_a := self.conversions.get(src, None):
			if a_to_b := from_a.get(dst, None):
				return a_to_b
		
		# Try identity
		if src == dst:
			return self.cached(IdentityTimeMapper(src))
		
		# Try backwards
		if from_b := self.conversions.get(dst, None):
			if b_to_a := from_b.get(src, None):
				return self.cached(-b_to_a)
		# No direct path found
		return None
	
	def neighbors(self, src: 'Clock') -> Sequence[TimeMapper]:
		if from_src := self.conversions.get(src, dict()):
			res = [value for value, _was_cached in from_src.values()]
			if src not in from_src.keys():
				res.append(IdentityTimeMapper(src))
			return res
		else:
			# Always provide identity
			return [IdentityTimeMapper(src)]

	def get_conversion(self, src: 'Clock', dst: 'Clock') -> Optional[TimeMapper]:
		import heapq
		prev: dict['Clock', tuple[int, TimeMapper]] = dict()
		# prev[src] = (0, None)
		queue: list[tuple[int,'Clock']] = [(0, src)]
		if src == dst:
			return self.cached(IdentityTimeMapper(src))

		def get_cost(node: 'Clock'):
			try:
				return prev[node][0]
			except KeyError:
				return float('inf')
		
		while len(queue) > 0:
			dist, node = heapq.heappop(queue)
			# Nodes can get added to the priority queue multiple times. We only
			# process a vertex the first time we remove it from the priority queue.
			if dist > get_cost(node):
				# print(" -> skip(bad entry)")
				continue
			
			for neighbor in self.neighbors(node):
				assert neighbor.clock_a == node
				n_cost = neighbor.conversion_cost
				assert n_cost > 0
				n_dist = dist + n_cost
				# print(" -> neighbor", neighbor, 'cost=', n_cost, 'dist=', n_dist, n_dist < get_cost(neighbor.clock_b), n_dist < get_cost(dst))
				# Only consider this new path if it's better than any path we've already found (both src->neighbor and src->dst)
				if (n_dist < get_cost(neighbor.clock_b)) and (n_dist < get_cost(dst)):
					prev[neighbor.clock_b] = (n_dist, neighbor)
					heapq.heappush(queue, (n_dist, neighbor.clock_b))
		
		if last := prev.get(dst, None):
			# Find path
			path = list()
			while last:
				# print('Path', last[1], 'maps', last[1].clock_a, '->', last[1].clock_b)
				path.append(last[1])
				if last[1].clock_a == src:
					break
				last = prev[last[1].clock_a]
			return ChainedTimeMapper(list(reversed(path)))
		else:
			# No path
			return None

MAP_CTX: 'contextvars.ContextVar[TimeMap]' = contextvars.ContextVar('TimeMap', default=TimeMap())


class InverseTimeMapper(TimeMapper):
	def __init__(self, parent: TimeMapper):
		super().__init__(parent.clock_b, parent.clock_a)
		self._parent = parent
	
	def get_offset(self) -> int:
		return -self._parent.get_offset()

	@property
	def constant_offset(self):
		return self._parent.constant_offset
	
	@property
	def conversion_cost(self):
		# Slightly more than forwards
		return self._parent.conversion_cost + 1
	
	def a_to_b(self, ts_a: 'Timestamp') -> 'Timestamp':
		return self._parent.b_to_a(ts_a)
	
	def b_to_a(self, ts_b: 'Timestamp') -> 'Timestamp':
		return self._parent.a_to_b(ts_b)

	def __neg__(self) -> 'TimeMapper':
		return self._parent

	def __repr__(self):
		return f'-{self._parent!r}'
	def __str__(self):
		return f'-{self._parent}'

class ChainedTimeMapper(TimeMapper):
	"Chain a sequence of [TimeMapper]s"

	def __init__(self, steps: list[TimeMapper]):
		if len(steps) == 0:
			raise ValueError('No intermediate steps')
		super().__init__(steps[0].clock_a, steps[-1].clock_b)

		# Flatten chains
		self.steps: list['TimeMapper'] = list()
		last_clock = None
		for step in steps:
			if isinstance(step, ChainedTimeMapper):
				for step_inner in step.steps:
					# Check that adjacent pairs are contiguous
					if last_clock is not None: assert step_inner.clock_a == last_clock
					last_clock = step_inner.clock_b

					assert not isinstance(step_inner, ChainedTimeMapper)
					self.steps.append(step_inner)
			elif isinstance(step, IdentityTimeMapper):
				if last_clock is not None: assert step.clock_a == last_clock
				last_clock = step.clock_b
				if len(steps) == 1:
					# Include identity if nothing else
					self.steps.append(step)
			else:
				# Check that adjacent pairs are contiguous
				if last_clock is not None: assert step.clock_a == last_clock
				last_clock = step.clock_b

				self.steps.append(step)
		
		# Oops all identity transforms
		
	
	@cached_property
	def constant_offset(self) -> bool:
		return all(step.constant_offset for step in self.steps)
	
	def get_offset(self) -> int:
		offset = 0
		for step in self.steps:
			offset += step.get_offset()
		return offset
	
	@cached_property
	def conversion_cost(self) -> int:
		return sum(step.conversion_cost for step in self.steps) + 1

	def __eq__(self, other) -> bool:
		if self is other:
			return True
		if isinstance(other, ChainedTimeMapper):
			if len(self.steps) != len(other.steps):
				return False
			for a, b in zip(self.steps, other.steps):
				if a != b:
					return False
			return True
		# Special case for single step
		if len(self.steps) == 1:
			return operator.eq(self.steps[0], other)
		return NotImplemented


class FixedOffsetMapper(TimeMapper):
	"""
	Try to compute the offset between the monotonic clock and system time
	We use this to convert timestamps to system time between processes
	"""

	@staticmethod
	def computed(clock_a: 'Clock', clock_b: 'Clock') -> 'FixedOffsetMapper':
		# Compute offset once
		ts_a_1 = clock_a.now_ns()
		ts_b = clock_b.now_ns()
		ts_a_2 = clock_a.now_ns()
		ts_a = (ts_a_1 + ts_a_2) // 2
		offset_ns = ts_b - ts_a
		return FixedOffsetMapper(clock_a, clock_b, offset_ns)

	def __init__(self, clock_a: 'Clock', clock_b: 'Clock', offset_ns: int) -> None:
		super().__init__(clock_a, clock_b)
		self.offset_ns = offset_ns
	
	@property
	def constant_offset(self):
		return True
	
	def get_offset(self):
		return self.offset_ns
	
	def __eq__(self, other) -> bool:
		if isinstance(other, FixedOffsetMapper):
			return (self.clock_a == other.clock_a) and (self.clock_b == other.clock_b) and (self.offset_ns == other.offset_ns)
		return super().__eq__(other)

class DynamicOffsetMapper(TimeMapper):
	"""
	Try to compute the offset between the monotonic clock and system time
	We use this to convert timestamps to system time between processes
	"""

	def __init__(self, clock_a: 'Clock', clock_b: 'Clock') -> None:
		super().__init__(clock_a, clock_b)
	
	@property
	def constant_offset(self):
		return False
	
	def get_offset(self):
		a = self.clock_a.now_ns()
		b = self.clock_b.now_ns()
		return b - a
	
	def __eq__(self, other) -> bool:
		if isinstance(other, DynamicOffsetMapper):
			return (self.clock_a == other.clock_a) and (self.clock_b == other.clock_b)
		return super().__eq__(other)


class IdentityTimeMapper(TimeMapper):
	def __init__(self, clock: 'Clock') -> None:
		super().__init__(clock, clock)
	
	@property
	def constant_offset(self):
		return True
	
	@property
	def conversion_cost(self):
		return 2
	
	def get_offset(self) -> int:
		return 0
	
	def __repr__(self):
		return f'{type(self).__name__}({self.clock_a!r})'
	def __str__(self):
		return f'{type(self).__name__}({self.clock_a})'
	
	def __eq__(self, other):
		if isinstance(other, IdentityTimeMapper):
			return self.clock_a == other.clock_a
		return super().__eq__(other)


class OffsetClockMapper(TimeMapper):
	"TimeMapper generated from an OffsetClock"
	clock_b: 'OffsetClock'
	def __init__(self, clock: 'OffsetClock') -> None:
		super().__init__(clock.base, clock)
	
	@property
	def constant_offset(self) -> bool:
		return self.clock_b.constant_offset
	
	def get_offset(self) -> int:
		return self.clock_b.get_offset_ns()
	
	def __hash__(self):
		return hash(self.clock_b)
	
	def __repr__(self):
		if self.constant_offset:
			offset = self.get_offset()
			return f'{type(self).__name__}({self.clock_a} {"+" if offset >= 0 else "-"} {abs(offset)}ns)'
		return f'{type(self).__name__}({self.clock_b!r})'

	def __eq__(self, other):
		if isinstance(other, OffsetClockMapper):
			return self.clock_b == other.clock_b
		return super().__eq__(other)