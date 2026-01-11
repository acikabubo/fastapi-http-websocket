from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    TypeVar,
    Union,
)

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.request import RequestModel

if TYPE_CHECKING:
    from app.schemas.response import ResponseModel

GenericSQLModelType = TypeVar("GenericSQLModelType", bound=SQLModel)

# Type definitions
JsonSchemaType = dict[
    str, Union[str, int, float, bool, list[Any], "JsonSchemaType"]
]
ValidatorType = Callable[
    [RequestModel, JsonSchemaType], Optional["ResponseModel"]
]
HandlerCallableType = Callable[
    [RequestModel, AsyncSession], Optional["ResponseModel"]
]
