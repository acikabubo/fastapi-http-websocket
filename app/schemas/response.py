from typing import Any, Generic
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from app.api.ws.constants import PkgID, RSPCode
from app.schemas.generic_typing import GenericSQLModelType


class MetadataModel(BaseModel):
    page: Annotated[int, Field(ge=1)]
    per_page: Annotated[int, Field(ge=1)]
    total: Annotated[int, Field(ge=0)]
    pages: Annotated[int, Field(ge=0)]


class BroadcastDataModel[GenericSQLModelType](BaseModel):
    pkg_id: PkgID = Field(frozen=True)
    req_id: UUID = Field(default=UUID(int=0), frozen=True)
    data: dict[str, Any] | list[GenericSQLModelType]


class ResponseModel[GenericSQLModelType](BaseModel):
    pkg_id: PkgID = Field(frozen=True)
    req_id: UUID = Field(frozen=True)
    status_code: RSPCode | None = RSPCode.OK
    meta: MetadataModel | dict | None = None
    data: dict[str, Any] | list[GenericSQLModelType] | None = None

    @classmethod
    def ok_msg(
        cls,
        pkg_id: PkgID,
        req_id: UUID,
        data: dict[str, Any] | None = None,
        msg: str | None = None,
    ) -> "ResponseModel":
        if data is None:
            data = {}
        if msg:
            data["msg"] = msg
        return cls(
            pkg_id=pkg_id, req_id=req_id, status_code=RSPCode.OK, data=data
        )

    @classmethod
    def err_msg(
        cls,
        pkg_id: PkgID,
        req_id: UUID,
        data: dict[str, Any] | None = None,
        msg: str | None = None,
        status_code: RSPCode | None = RSPCode.ERROR,
    ) -> "ResponseModel":
        if data is None:
            data = {}
        if msg:
            data["msg"] = msg
        return cls(
            pkg_id=pkg_id, req_id=req_id, status_code=status_code, data=data
        )


class PaginatedResponseModel(BaseModel, Generic[GenericSQLModelType]):
    items: list[GenericSQLModelType]
    meta: MetadataModel
