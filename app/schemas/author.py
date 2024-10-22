from typing import Annotated, TypedDict

from fastapi import Query
from pydantic import BaseModel


class AuthorFilters(TypedDict, total=False):
    id: int
    name: str


class AuthorQueryParams(BaseModel):
    name: Annotated[str | None, Query(max_length=30)] = None
