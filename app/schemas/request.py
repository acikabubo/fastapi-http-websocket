from typing import Any, Optional
from pydantic import BaseModel, Field
from typing_extensions import Annotated
from app.api.ws.constants import PkgID
from uuid import UUID


class RequestModel(BaseModel):
    pkg_id: PkgID
    req_id: UUID
    method: Optional[str] = ""
    data: Optional[dict[str, Any]] = {}


class PaginatedRequestModel(BaseModel):
    page: Annotated[int, Field(gt=1)]
    per_page: Annotated[int, Field(gt=1)]
