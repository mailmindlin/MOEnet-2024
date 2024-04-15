from typing import ClassVar, Optional, Callable, Iterable, Any, Annotated, Union, Literal
import numpy as np
import numpy.typing as npt
from pydantic import PositiveInt, BaseModel
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue
from pydantic import FilePath, GetJsonSchemaHandler, PositiveInt, validate_call

type SupportedDTypes = np.dtype
# NpArrayPydanticAnnotation.factory(data_type=None, dimensions=1, strict_data_typing=False),

type NDArray[Shape, DType: np.dtype] = np.ndarray[Shape, DType]


class NpArrayPydanticAnnotation:
    dimensions: ClassVar[Optional[PositiveInt]]
    data_type: ClassVar[SupportedDTypes]

    strict_data_typing: ClassVar[bool]

    serialize_numpy_array_to_json: ClassVar[Callable[[npt.ArrayLike], Iterable]]
    json_schema_from_type_data: ClassVar[
        Callable[
            [core_schema.CoreSchema, GetJsonSchemaHandler, Optional[PositiveInt], Optional[SupportedDTypes]],
            JsonSchemaValue,
        ]
    ]

    @classmethod
    def factory(
        cls,
        *,
        data_type: Optional[SupportedDTypes] = None,
        dimensions: Optional[PositiveInt] = None,
        strict_data_typing: bool = False,
        serialize_numpy_array_to_json: Callable[
            [npt.ArrayLike], Iterable
        ] = pd_np_native_numpy_array_to_data_dict_serializer,
        json_schema_from_type_data: Callable[
            [core_schema.CoreSchema, GetJsonSchemaHandler, Optional[PositiveInt], Optional[SupportedDTypes]],
            JsonSchemaValue,
        ] = pd_np_native_numpy_array_json_schema_from_type_data,
    ) -> type:
        """
        Create an instance NpArrayPydanticAnnotation that is configured for a specific dimension and dtype.

        The signature of the function is data_type, dimension and not dimension, data_type to reduce amount of
        code for all the types.

        Parameters
        ----------
        data_type: SupportedDTypes
        dimensions: Optional[PositiveInt]
            If defined, the number of dimensions determine the depth of the numpy array. Defaults to None,
            e.g. any number of dimensions
        strict_data_typing: bool
            If True, the dtype of the numpy array must be identical to the data_type. No conversion attempts.
        serialize_numpy_array_to_json: Callable[[npt.ArrayLike], Iterable]
            Json serialization function to use. Defaults to NumpyArrayTypeData serializer.
        json_schema_from_type_data: Callable
            Json schema generation function to use. Defaults to NumpyArrayTypeData schema generator.

        Returns
        -------
        NpArrayPydanticAnnotation
        """
        if strict_data_typing and not data_type:
            msg = "Strict data typing requires data_type (SupportedDTypes) definition"
            raise ValueError(msg)

        return type(
            (
                f"Np{'Strict' if strict_data_typing else ''}{dimensions or 'N'}DArray"
                f"{data_type.__name__.capitalize() if data_type else ''}PydanticAnnotation"
            ),
            (cls,),
            {
                "dimensions": dimensions,
                "data_type": data_type,
                "strict_data_typing": strict_data_typing,
                "serialize_numpy_array_to_json": serialize_numpy_array_to_json,
                "json_schema_from_type_data": json_schema_from_type_data,
            },
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        np_array_validator = create_array_validator(cls.dimensions, cls.data_type, cls.strict_data_typing)
        np_array_schema = core_schema.no_info_plain_validator_function(np_array_validator)

        return core_schema.json_or_python_schema(
            python_schema=core_schema.chain_schema([_common_numpy_array_validator, np_array_schema]),
            json_schema=np_array_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.serialize_numpy_array_to_json,
                is_field_serializer=False,
                when_used="json-unless-none",
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, field_core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return cls.json_schema_from_type_data(field_core_schema, handler, cls.dimensions, cls.data_type)


def np_array_pydantic_annotated_typing(
    data_type: Optional[SupportedDTypes] = None,
    dimensions: Optional[int] = None,
    strict_data_typing: bool = False,
    serialize_numpy_array_to_json: Callable[[npt.ArrayLike], Iterable] = pd_np_native_numpy_array_to_data_dict_serializer,
):
    """
    Generates typing and pydantic annotation of a np.ndarray parametrized with given constraints

    Parameters
    ----------
    data_type: SupportedDTypes
    dimensions: Optional[int]
        Number of dimensions determine the depth of the numpy array.
    strict_data_typing: bool
        If True, the dtype of the numpy array must be identical to the data_type. No conversion attempts.
    serialize_numpy_array_to_json: Callable[[npt.ArrayLike], Iterable]
        Json serialization function to use. Defaults to NumpyArrayTypeData serializer.

    Returns
    -------
    type-hint for np.ndarray with Pydantic support

    Note
    ----
    The function generates the type hints dynamically, and will not work with static type checkers such as mypy
    or pyright. For that you need to create your types manually.
    """
    return Annotated[
        Union[
            FilePath,
            MultiArrayNumpyFile,
            np.ndarray[  # type: ignore[misc]
                _dimensions_to_shape_type[dimensions]  # pyright: ignore[reportGeneralTypeIssues]
                if dimensions
                else Any,
                np.dtype[data_type] if _data_type_resolver(data_type) else data_type,  # type: ignore[valid-type]
            ],
        ],
        NpArrayPydanticAnnotation.factory(
            data_type=data_type,
            dimensions=dimensions,
            strict_data_typing=strict_data_typing,
            serialize_numpy_array_to_json=serialize_numpy_array_to_json,
        ),
    ]