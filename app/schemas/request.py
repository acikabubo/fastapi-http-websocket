from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from app.api.ws.constants import PkgID


class RequestModel(BaseModel):
    """
    Base model for WebSocket requests.

    Attributes:
        pkg_id: Package ID identifying the handler to route to.
        req_id: Unique request identifier for tracking.
        method: Optional method name for the request.
        data: Optional dictionary containing request payload.
    """

    pkg_id: PkgID = Field(frozen=True)
    req_id: UUID = Field(frozen=True)
    method: Optional[str] = ""
    data: Optional[dict[str, Any]] = {}


class PaginatedRequestModel(BaseModel):
    """
    Model for paginated request parameters.

    Attributes:
        page: Page number to retrieve (starts from 1).
        per_page: Number of items per page.
    """

    page: Annotated[int, Field(ge=1)]
    per_page: Annotated[int, Field(ge=1)]
