from typing import Any, Generic, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from app.api.ws.constants import PkgID, RSPCode
from app.schemas.generic_typing import GenericSQLModelType


class MetadataModel(BaseModel):
    page: Annotated[int, Field(gt=1)]
    per_page: Annotated[int, Field(gt=1)]
    total: Annotated[int, Field(gt=0)]
    pages: Annotated[int, Field(gt=0)]


class BroadcastDataModel[GenericSQLModelType](BaseModel):
    pkg_id: PkgID
    req_id: UUID
    data: dict[str, Any] | list[GenericSQLModelType]


class ResponseModel[GenericSQLModelType](BaseModel):
    pkg_id: PkgID
    req_id: UUID
    status_code: Optional[RSPCode] = RSPCode.OK
    meta: Optional[MetadataModel | dict] = {}
    data: Optional[dict[str, Any] | list[GenericSQLModelType]] = {}

    @classmethod
    def ok_msg(
        cls,
        pkg_id: RSPCode,
        req_id: UUID,
        data: Optional[dict[str, Any]] = {},
        msg: Optional[str] = None,
    ) -> "ResponseModel":
        if msg:
            data["msg"] = msg
        return cls(
            pkg_id=pkg_id, req_id=req_id, status_code=RSPCode.OK, data=data
        )

    @classmethod
    def err_msg(
        cls,
        pkg_id: RSPCode,
        req_id: UUID,
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
