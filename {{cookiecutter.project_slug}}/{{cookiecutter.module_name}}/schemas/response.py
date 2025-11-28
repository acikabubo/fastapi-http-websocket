from typing import Any, Generic, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from {{cookiecutter.module_name}}.api.ws.constants import PkgID, RSPCode
from {{cookiecutter.module_name}}.schemas.generic_typing import GenericSQLModelType


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
    status_code: Optional[RSPCode] = RSPCode.OK
    meta: Optional[MetadataModel | dict] = None
    data: Optional[dict[str, Any] | list[GenericSQLModelType]] = None

    @classmethod
    def ok_msg(
        cls,
        pkg_id: PkgID,
        req_id: UUID,
        data: Optional[dict[str, Any]] = None,
        msg: Optional[str] = None,
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
        data: Optional[dict[str, Any]] = None,
        msg: Optional[str] = None,
        status_code: Optional[RSPCode] = RSPCode.ERROR,
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
