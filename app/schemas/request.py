from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from app.api.ws.constants import PkgID


class RequestModel(BaseModel):
    pkg_id: PkgID = Field(frozen=True)
    req_id: UUID = Field(frozen=True)
    method: Optional[str] = ""
    data: Optional[dict[str, Any]] = {}


class PaginatedRequestModel(BaseModel):
    page: Annotated[int, Field(ge=1)]
    per_page: Annotated[int, Field(ge=1)]
