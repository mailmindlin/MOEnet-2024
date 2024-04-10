from typing import ClassVar, Literal, Type, Self
import numpy as np
from .base import LinearCovariantBase

class RandomNormal(LinearCovariantBase[float, Literal[1]]):
	"Random normal variable"
	STATE_LEN: ClassVar[int] = 1

	@classmethod
	def wrap(cls: Type[Self], value: float | Self) -> Self:
		if isinstance(value, cls):
			return value
		else:
			return cls(float(value))

	@classmethod
	def parse_numpy(cls, mean: float | np.ndarray[tuple[Literal[1]], np.dtype[np.floating]]) -> float:
		arr = np.asanyarray(mean, dtype=np.float64)
		assert np.shape(arr) == (1,)
		return arr.item(0)
	
	def __float__(self):
		return self.mean

	def __mul__(self, scalar: float) -> 'RandomNormal':
		if isinstance(scalar, np.floating):
			return RandomNormal(self.mean * scalar, np.square(scalar) * self.cov)
		return NotImplemented
	__rmul__ = __mul__

	def __div__(self, scalar: float) -> 'RandomNormal':
		if isinstance(scalar, np.floating):
			return self * np.reciprocal(scalar)
		return NotImplemented
	
	def mean_vec(self) -> np.ndarray[tuple[Literal[1]], np.dtype[np.float64]]:
		return np.array([self.mean], dtype=np.float64)