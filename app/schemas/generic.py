from typing import TypeVar

from sqlmodel import SQLModel

GenericSQLModelType = TypeVar("GenericSQLModelType", bound=SQLModel)
