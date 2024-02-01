class classproperty:
	def __init__(self, method=None):
		self.fget = method

	def __get__(self, instance, cls=None):
		return self.fget(cls)

	def getter(self, method):
		self.fget = method
		return self

class cached_classproperty(classproperty):
	def __init__(self, method=None):
		self.fget = method

	def get_result_field_name(self):
		return self.fget.__name__ + "_property_result" if self.fget else None

	def __get__(self, instance, cls=None):
		result_field_name = self.get_result_field_name()

		if hasattr(cls, result_field_name):
			return getattr(cls, result_field_name)

		if not cls or not result_field_name:
			return self.fget(cls)

		setattr(cls, result_field_name, self.fget(cls))
		return getattr(cls, result_field_name)

	def getter(self, method):
		self.fget = method
		return self

class SingletonMeta(type):
	_instances = {}
	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
		return cls._instances[cls]

class Singleton:
	def __new__(cls):
		# pseudo-singleton
		if getattr(cls, '_instance', None) is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __repr__(self):
		return f'{type(self).__name__}()'
	__str__ = __repr__
