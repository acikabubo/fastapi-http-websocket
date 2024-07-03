from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import SQLModel

GenericSQLModelType = TypeVar("GenericSQLModelType", bound=SQLModel)


class AuthorCreateSchema(BaseModel):
    name: str


class BookCreateSchema(BaseModel):
    title: str
    author_id: Optional[int]


class GenreCreateSchema(BaseModel):
    name: str


class RequestModel(BaseModel):
    pkg_id: int
    req_id: str
    method: Optional[str] = ""
    data: Optional[dict[str, Any]] = {}


class ResponseModel[GenericSQLModelType](BaseModel):
    pkg_id: int
    req_id: str
    status_code: Optional[int] = 0
    data: Optional[dict[str, Any] | list[GenericSQLModelType]] = {}

    @classmethod
    def ok_msg(
        cls,
        pkg_id: int,
        req_id: Optional[UUID],
        data: dict[str, Any],
        msg: Optional[str] = None,
    ) -> "ResponseModel":
        if msg:
            data["msg"] = msg
        return cls(pkg_id=pkg_id, req_id=req_id, status_code=0, data=data)

    @classmethod
    def err_msg(
        cls,
        pkg_id: int,
        req_id: Optional[UUID],
        data: dict[str, Any],
        msg: Optional[str] = None,
    ) -> "ResponseModel":
        if msg:
            data["msg"] = msg
        return cls(pkg_id=pkg_id, req_id=req_id, status_code=-1, data=data)


class PaginatedResponseModel(BaseModel, Generic[GenericSQLModelType]):
    items: list[GenericSQLModelType]
    page: int
    per_page: int
    total: int
    pages: int
