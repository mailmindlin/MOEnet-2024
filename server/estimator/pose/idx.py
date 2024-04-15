from typing import Self
import numpy as np

class Slicable[T: type]:
	def __init__(self, arr: np.ndarray, key: T) -> None:
		self._arr = arr
		self._key = key
	
	def map_idxs(self, idxs: tuple):
		res = list()
		for idx in idxs:
			if isinstance(idx, self._key):
				idx = idx.idxs()
			res.append(idx)
		return tuple(res)
	def __getitem__(self, key):
		return self._arr[self.map_idxs(key)]
	def __getitem__(self, key, value):
		return self._arr[self.map_idxs(key)] = value