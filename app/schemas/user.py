from datetime import datetime

from pydantic import BaseModel, Field


class UserModel(BaseModel):
    id: str = Field(..., alias="sub")
    expired_in: int = Field(
        ..., alias="exp"
    )  # timestamp when keycloak session expires
    username: str = Field(..., alias="preferred_username")
    roles: list[str] = []

    # FIXME: Unnecessary fields, probably should be removed
    # given_name: str
    # family_name: str
    # email: str
    # attributes: dict[str, Any] = {}

    def __init__(self, **kwargs):
        # Get client roles
        kwargs["roles"] = (
            kwargs.get("resource_access", {})
            .get(kwargs["azp"], {})
            .get("roles", [])
        )

        super(UserModel, self).__init__(**kwargs)

    @property
    def expired_seconds(self):
        return self.expired_in - int(datetime.now().timestamp())

    # This method is use for caching in PackageRouter class
    def __hash__(self):
        return hash(self.id)
