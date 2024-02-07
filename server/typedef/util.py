from typing import TypeVar, Type, Annotated, Any, Callable
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from typing_extensions import TypeAliasType

T = TypeVar('T')
def wrap_dai_enum(dai_enum: Type[T]) -> Type[T]:
	members: dict[str, T] = dai_enum.__members__
	def validate_from_str(value: str) -> T:
		return members[value]
	
	def validate_from_int(value: int) -> T:
		for v in members.values():
			if v.value == value:
				return v
		raise KeyError(f'Unknown value {value}')
	from_str_schema = core_schema.chain_schema(
		[
			core_schema.literal_schema(list(members.keys())),
			core_schema.no_info_plain_validator_function(validate_from_str),
		]
	)
	from_int_schema = core_schema.chain_schema(
		[
			core_schema.int_schema(),
			core_schema.no_info_plain_validator_function(validate_from_int),
		]
	)

	class _DaiEnumHelper:
		@classmethod
		def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Callable[[Any], core_schema.CoreSchema]) -> core_schema.CoreSchema:
			return core_schema.json_or_python_schema(
				json_schema=from_str_schema,
				python_schema=core_schema.union_schema(
					[
						# check if it's an instance first before doing any further work
						core_schema.is_instance_schema(dai_enum),
						from_str_schema,
						from_int_schema,
					]
				),
				serialization=core_schema.plain_serializer_function_ser_schema(
					lambda instance: instance.name
				),
			)

		@classmethod
		def __get_pydantic_json_schema__(cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
			# Use the same schema that would be used for `int`
			return handler(from_str_schema)

	_TypeAliasType: Any = TypeAliasType
	name: str = dai_enum.__qualname__.replace('.', '$')
	return _TypeAliasType(name, Annotated[dai_enum, _DaiEnumHelper])
