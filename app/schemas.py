from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuthorCreateSchema(BaseModel):
    name: str


class BookCreateSchema(BaseModel):
    title: str
    author_id: Optional[int]


class GenreCreateSchema(BaseModel):
    name: str


class RequestModel(BaseModel):
    pkg_id: int
    req_id: Optional[UUID]
    method: str
    data: Dict


class ResponseModel(BaseModel):
    pkg_id: int
    req_id: Optional[UUID]
    status_code: int
    data: Optional[Dict]

    @classmethod
    def ok_msg(
        cls,
        pkg_id: int,
        req_id: Optional[UUID],
        data: Dict,
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
        data: Dict,
        msg: Optional[str] = None,
    ) -> "ResponseModel":
        if msg:
            data["msg"] = msg
        return cls(pkg_id=pkg_id, req_id=req_id, status_code=-1, data=data)
