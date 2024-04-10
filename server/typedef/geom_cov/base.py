from typing import TypeVar, Self, Generic, ClassVar, overload
from abc import ABC, abstractmethod

from pydantic import PositiveInt
import numpy as np


T = TypeVar('T')
N = TypeVar('N', bound=int)

def mahalanobisDistance2(mean_diff: np.ndarray[tuple[N], np.dtype[np.floating]], cov_sum: np.ndarray[tuple[N, N], np.dtype[np.floating]]) -> float:
	"Squared mahalanobis distance"
	cov_inv = np.linalg.inv(cov_sum)
	return (cov_inv.T @ mean_diff @ cov_inv).item(0)

def mahalanobisDistance(mean_diff: np.ndarray[tuple[N], np.dtype[np.floating]], cov_sum: np.ndarray[tuple[N, N], np.dtype[np.floating]]) -> float:
	return np.sqrt(mahalanobisDistance2(mean_diff, cov_sum))

class Covariant(ABC, Generic[N]):
	"Abstract base type for data with mean and covariance matrix"
	STATE_LEN: ClassVar[int] = 0

	cov: np.ndarray[tuple[N, N], np.dtype[np.floating]]
	"Covariance matrix"

	def __init__(self, cov: np.ndarray[tuple[N, N], np.dtype[np.floating]] | None = None) -> None:
		super().__init__()
		if cov is None:
			cov = np.zeros((self.STATE_LEN, self.STATE_LEN), dtype=float)
		else:
			cov = np.asanyarray(cov)
		assert np.shape(cov) == (self.STATE_LEN, self.STATE_LEN)
		self.cov = cov
	
	def isfinite(self) -> bool:
		"Are the mean and covariance matrix elements all finite?"
		return bool(np.all(np.isfinite(self.mean_vec())) and np.all(np.isfinite(self.cov)))
	
	@abstractmethod
	def mean_vec(self) -> np.ndarray[tuple[N], np.dtype[np.floating]]:
		"Get mean, as numpy array"
		pass


class CovariantWrapper(Covariant[N], Generic[T, N]):
	"Wrapper to help add covariance matrix to a type"
	@classmethod
	def parse_numpy(cls, mean: T | np.ndarray[tuple[N], np.dtype[np.floating]]) -> T:
		"Parse numpy array as datatype"
		return mean
	
	def __init__(self, mean: T | np.ndarray[tuple[N], np.dtype[np.floating]], cov: np.ndarray[tuple[N, N], np.dtype[np.floating]] | None = None):
		super().__init__(cov)
		self.mean = type(self).parse_numpy(mean)
	
	def __iter__(self):
		return self
	
	def __next__(self):
		return self.sample()
	
	@overload
	def sample(self) -> T:
		"Sample a single possible value from this distribution"
	@overload
	def sample(self, n: PositiveInt) -> list[T]:
		"Sample multiple values from this distribution"
	def sample(self, n: PositiveInt | None = None):
		mean_np = self.mean_vec()
		assert (n is None) or (n > 0)

		sample = np.random.multivariate_normal(mean_np, self.cov, n)

		# We need to help out the type checker a bit
		def parse_numpy(v: np.ndarray[tuple[N], np.dtype[np.floating]]) -> T:
			return type(self).parse_numpy(v)
		
		if n is None:
			return parse_numpy(sample)
		else:
			return [
				parse_numpy(sample[i])
				for i in range(n)
			]
	
	def __repr__(self):
		return f'{type(self).__name__}(mean={self.mean!r}, cov={self.cov})'
	# def __matmul__(self, tf: np.ndarray[tuple[N], np.dtype[np.floating]]):
	# 	pass

class LinearCovariantBase(CovariantWrapper[T, N]):
	"CovariantWrapper with some extra methods assuming T is linear"
	@classmethod
	def _try_wrap(cls, other: T | Self | np.ndarray[tuple[N], np.dtype[np.floating]]) -> Self:
		if isinstance(other, cls):
			return other
		try:
			other = cls.parse_numpy(other)
		except:
			return NotImplemented
		assert isinstance(other, cls)
		return other
	
	def __neg__(self) -> Self:
		return type(self)(-self.mean_vec(), self.cov)
	
	def __pos__(self):
		return self

	def __add__(self, other: T | Self | np.ndarray[tuple[N], np.dtype[np.floating]]) -> Self:
		cls = type(self)
		other = cls._try_wrap(other)
		if isinstance(other, cls):
			return cls(self.mean_vec() + other.mean_vec(), self.cov + other.cov)
		return NotImplemented
	
	__radd__ = __add__
	
	def __sub__(self, other: T | Self | np.ndarray[tuple[N], np.dtype[np.floating]]) -> Self:
		cls = type(self)
		other = cls._try_wrap(other)
		if isinstance(other, cls):
			return cls(self.mean_vec() - other.mean_vec(), self.cov + other.cov)
		return NotImplemented
	
	def __rsub__(self, other: T | Self | np.ndarray[tuple[N], np.dtype[np.floating]]) -> Self:
		cls = type(self)
		other = cls._try_wrap(other)
		if isinstance(other, cls):
			return cls(other.mean_vec() - self.mean_vec(), self.cov + other.cov)
		return NotImplemented