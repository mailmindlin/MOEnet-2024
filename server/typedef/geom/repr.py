"Field representation"
from typing import Optional, Union, Self, Sequence
from dataclasses import dataclass

@dataclass
class FieldDesc[F]:
	"Explicitly describe a field"
	type: type[F]
	"Field type"
	getter: Optional[str] = None
	"Field getter method name"


@dataclass
class FieldInfo[T, F]:
	@classmethod
	def wrap(cls, name: str, base: type[T], value: Union[type[F], FieldDesc]) -> Self:
		getter = None
		if isinstance(value, FieldDesc):
			type = value.type
			getter = value.getter
		else:
			type = value
		return cls(
			name=name,
			base=base,
			type=type,
			getter=getter
		)
	
	name: str
	"Field name"
	base: type[T]
	"Data type that owns this field"
	type: type[F]
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


def lookup_fields[T, R](fields: Sequence[FieldInfo[T, R]], value: T):
	"Get named fields as a list"
	for field in fields:
		yield field.get(value)