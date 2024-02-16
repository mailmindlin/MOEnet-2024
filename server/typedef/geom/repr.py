"Field representation"
from typing import TypeVar, Generic, Type, Optional, Union, Any
from dataclasses import dataclass

T = TypeVar('T')
F = TypeVar('F')

@dataclass
class FieldDesc(Generic[F]):
	"Explicitly describe a field"
	type: Type[F]
	"Field type"
	getter: Optional[str] = None
	"Field getter method name"


@dataclass
class FieldInfo(Generic[T, F]):
	@staticmethod
	def wrap(name: str, base: Type[T], value: Union[Type[F], FieldDesc]) -> 'FieldInfo[T, F]':
		getter = None
		if isinstance(value, FieldDesc):
			type = value.type
			getter = value.getter
		else:
			type = value
		return FieldInfo(
			name=name,
			base=base,
			type=type,
			getter=getter
		)
	
	name: str
	"Field name"
	base: Type[T]
	"Data type that owns this field"
	type: Type[F]
	"Field type"
	getter: Optional[str] = None
	"Field getter method name"

	def doc(self) -> Optional[str]:
		"Field docstring"
		if entry := getattr(self.base, self.name, None):
			if doc := getattr(entry, '__doc__', None):
				return doc

	def get(self, value: T) -> F:
		"Get the value of this field from an instance of `T`"
		name = self.getter if self.getter is not None else self.name
		res = getattr(value, name)
		if callable(res):
			res = res()
		return res


def lookup_fields(fields: list[FieldInfo[T, Any]], value: T):
	"Get named fields as a list"
	for field in fields:
		yield field.get(value)