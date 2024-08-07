from typing import Any, Generic, Optional
from uuid import UUID

from pydantic import BaseModel

from app.api.ws.constants import RSPCode
from app.schemas.generic_typing import GenericSQLModelType


class MetadataModel(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int


class ResponseModel[GenericSQLModelType](BaseModel):
    pkg_id: int
    req_id: str
    status_code: Optional[int] = 0
    meta: Optional[MetadataModel | dict] = {}
    data: Optional[dict[str, Any] | list[GenericSQLModelType]] = {}

    @classmethod
    def ok_msg(
        cls,
        pkg_id: int,
        req_id: Optional[UUID],
        data: Optional[dict[str, Any]] = {},
        msg: Optional[str] = None,
    ) -> "ResponseModel":
        if msg:
            data["msg"] = msg
        return cls(pkg_id=pkg_id, req_id=req_id, status_code=0, data=data)

    @classmethod
    def err_msg(
        cls,
        pkg_id: int,
        req_id: Optional[UUID | str] = "",
        data: Optional[dict[str, Any]] = {},
        msg: Optional[str] = None,
        status_code: Optional[RSPCode] = RSPCode.ERROR,
    ) -> "ResponseModel":
        if msg:
            data["msg"] = msg
        return cls(
            pkg_id=pkg_id, req_id=req_id, status_code=status_code, data=data
        )


class PaginatedResponseModel(BaseModel, Generic[GenericSQLModelType]):
    items: list[GenericSQLModelType]
    meta: MetadataModel
