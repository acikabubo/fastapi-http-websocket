from datetime import datetime

from pydantic import BaseModel, Field


class UserModel(BaseModel):  # type: ignore[misc]
    id: str = Field(..., alias="sub")
    expired_in: int = Field(
        ..., alias="exp"
    )  # timestamp when keycloak session expires
    username: str = Field(..., alias="preferred_username")
    roles: list[str] = []

    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        # Get client roles
        kwargs["roles"] = (
            kwargs.get("resource_access", {})
            .get(kwargs["azp"], {})
            .get("roles", [])
        )

        super(UserModel, self).__init__(**kwargs)

    @property
    def expired_seconds(self) -> int:
        return self.expired_in - int(datetime.now().timestamp())

    # This method is use for caching in PackageRouter class
    def __hash__(self) -> int:
        return hash(self.id)
