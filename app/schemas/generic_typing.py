from collections.abc import Awaitable
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    Protocol,
    TypeVar,
    Union,
)

from sqlmodel import SQLModel

from app.schemas.request import RequestModel

if TYPE_CHECKING:
    from app.schemas.response import ResponseModel

GenericSQLModelType = TypeVar("GenericSQLModelType", bound=SQLModel)


class PydanticModel(Protocol):
    """Protocol for Pydantic models with model_json_schema method."""

    def model_json_schema(self) -> dict[str, Any]: ...


# Type definitions
JsonSchemaType = (
    dict[str, Union[str, int, float, bool, list[Any], "JsonSchemaType"]]
    | type[PydanticModel]
)
ValidatorType = Callable[
    [RequestModel, JsonSchemaType], Optional["ResponseModel[Any]"]
]
HandlerCallableType = Callable[[RequestModel], Awaitable["ResponseModel[Any]"]]
