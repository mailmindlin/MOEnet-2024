from datetime import timedelta
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class FilterBase:
	def reset(self): ...


class PoseEstimator:
	pass