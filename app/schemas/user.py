from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserModel(BaseModel):
    id: str = Field(..., alias="sub")
    given_name: str
    family_name: str
    email: str
    expired_in: int = Field(
        ..., alias="exp"
    )  # timestamp when keycloak session expires
    username: str = Field(..., alias="preferred_username")
    roles: list[str] = []
    attributes: dict[str, Any] = {}

    def __init__(self, **kwargs):
        kwargs["roles"] = kwargs.get("realm_access", {}).get("roles", [])

        super(UserModel, self).__init__(**kwargs)

    @property
    def expired_seconds(self):
        return self.expired_in - int(datetime.now().timestamp())

    # This method is use for caching in PackageRouter class
    def __hash__(self):
        return hash(self.id)
