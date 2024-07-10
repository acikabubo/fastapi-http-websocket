from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.request import RequestModel

GenericSQLModelType = TypeVar("GenericSQLModelType", bound=SQLModel)

# Type definitions
JsonSchemaType = Dict[
    str, Union[str, int, float, bool, List[Any], "JsonSchemaType"]
]
ValidatorType = Callable[
    [RequestModel, JsonSchemaType], Optional["ResponseModel"]
]
HandlerCallableType = Callable[
    [RequestModel, AsyncSession], Optional["ResponseModel"]
]
