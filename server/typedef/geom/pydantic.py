"Add compatibility between wpilib geometry/Pydantic schemas"
from typing import Any
from dataclasses import dataclass
from wpiutil import wpistruct
from pydantic_core import core_schema
from pydantic import (
	GetCoreSchemaHandler,
	GetJsonSchemaHandler,
)
from pydantic.json_schema import JsonSchemaValue

from .repr import FieldInfo

SCHEMA_LUT = {
	int: core_schema.int_schema(),
	float: core_schema.float_schema(),
	wpistruct.double: core_schema.float_schema(),
}
"python type -> schema lookup"
CUSTOM_SCHEMA: dict[type, 'CustomSchemaInfo'] = dict()

@dataclass
class CustomSchemaInfo[T]:
	type: type[T]
	fields: list[FieldInfo]
	schema: Any

	def serialize_json(self, value: T):
		res = dict()
		for field in self.fields:
			fval = field.get(value)
			if custom := CUSTOM_SCHEMA.get(field.type, None):
				fval = custom.serialize_json(fval)
			res[field.name] = fval
		return res
	def parse_json(self, raw: Any) -> T:
		values = list()
		for field in self.fields:
			value = raw[field.name]
			if custom := CUSTOM_SCHEMA.get(field.type, None):
				value = custom.parse_json(value)
			values.append(value)
		return self.type(*values)


def make_schema[T](t: type[T], fields: list[FieldInfo]):
	tdfs = dict()
	for field in fields:
		base = SCHEMA_LUT.get(field.type, None) or CUSTOM_SCHEMA[field.type].schema
		tdf = core_schema.typed_dict_field(base, required=True)
		#TODO: figure out how to set description fields
		# if desc := field.doc():
		# 	print(f'Map field {t.__name__}.{field.name} -> {desc}')
		# 	tdf['description'] = desc
		tdfs[field.name] = tdf
	schema = core_schema.typed_dict_schema(tdfs)
	result = CustomSchemaInfo(t, fields, schema)
	# Register this schema
	CUSTOM_SCHEMA[t] = result
	return result

def add_pydantic_validator[T](t: type[T], fields: list[FieldInfo]):
	schema = make_schema(t, fields)

	@classmethod
	def __get_pydantic_core_schema__(
		cls: type[T],
		_source_type: Any,
		_handler: GetCoreSchemaHandler,
	) -> core_schema.CoreSchema:
		json_schema = core_schema.chain_schema(
			[
				schema.schema,
				core_schema.no_info_plain_validator_function(schema.parse_json),
			]
		)

		return core_schema.json_or_python_schema(
			json_schema=json_schema,
			python_schema=core_schema.union_schema(
				[
					# check if it's an instance first before doing any further work
					core_schema.is_instance_schema(t),
					json_schema,
				]
			),
			serialization=core_schema.plain_serializer_function_ser_schema(schema.serialize_json),
		)

	@classmethod
	def __get_pydantic_json_schema__(cls: type[T], _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
		return handler(schema.schema)
	
	# Modify class
	setattr(t, '__get_pydantic_core_schema__', __get_pydantic_core_schema__)
	setattr(t, '__get_pydantic_json_schema__', __get_pydantic_json_schema__)