from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from {{cookiecutter.module_name}}.api.ws.constants import PkgID


class RequestModel(BaseModel):
    pkg_id: PkgID = Field(frozen=True)
    req_id: UUID = Field(frozen=True)
    method: Optional[str] = ""
    data: Optional[dict[str, Any]] = {}


class PaginatedRequestModel(BaseModel):
    page: int = 1
    per_page: int = 2
