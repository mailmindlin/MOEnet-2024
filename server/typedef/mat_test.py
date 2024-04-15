from unittest import TestCase
import numpy as np
from .mat import NDArray
from pydantic import TypeAdapter, BaseModel, RootModel

type Array1d[DType: np.dtype] = NDArray[tuple[int], DType]
type Array1dAny = Array1d[np.dtype[np.generic]]
type Array1dFloating = Array1d[np.dtype[np.floating]]
type Array1dF32 = Array1d[np.dtype[np.float32]]
type Array1dInt = Array1d[np.dtype[np.integer]]
type Array1dI32 = Array1d[np.dtype[np.int32]]

class Numpy1d(TestCase):
    def test_int_is_any(self):
        adapter_1d = TypeAdapter(Array1dAny)
        src = np.array([1,2,3], dtype=int)
        res = adapter_1d.validate_python(src)
        assert src == res
    
    def test_float_is_any(self):
        adapter_1d = TypeAdapter(Array1dAny)
        src = np.array([1,2,3], dtype=float)
        res = adapter_1d.validate_python(src)
        assert src == res