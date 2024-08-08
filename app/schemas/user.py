from pydantic import BaseModel


class UserModel(BaseModel):
    firstname: str
    lastname: str
    email: str
    username: str
    roles: list[str] = []
