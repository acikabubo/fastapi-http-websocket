from typing import Any, Optional

from pydantic import BaseModel


class RequestModel(BaseModel):
    pkg_id: int
    req_id: str
    method: Optional[str] = ""
    data: Optional[dict[str, Any]] = {}


class PaginatedRequestModel(BaseModel):
    page: int = 1
    per_page: int = 2
