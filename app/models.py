from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class BaseModel(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, index=True)


class Author(BaseModel, table=True):
    name: str
    books: List["Book"] = Relationship(back_populates="author")


class Book(BaseModel, table=True):
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    author: Optional[Author] = Relationship(back_populates="books")


class Association(BaseModel, table=True):
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    genre_id: Optional[int] = Field(default=None, foreign_key="genre.id")


class Genre(BaseModel, table=True):
    name: str
    authors: List[Author] = Relationship(
        back_populates="genres", link_model=Association
    )


Author.genres = Relationship(back_populates="authors", link_model=Association)


class ResponseModel(SQLModel):
    pkg_id: int
    req_id: Optional[UUID]
    status_code: int
    data: Optional[dict]

    @classmethod
    def ok_msg(
        cls, pkg_id: int, req_id: Optional[UUID], data: dict
    ) -> "ResponseModel":
        """
        Create a ResponseModel instance with a status_code of 0, indicating a successful response.

        Args:
            pkg_id (int): The package ID associated with the response.
            req_id (Optional[UUID]): The request ID associated with the response.
            data (dict): The data to be included in the response.

        Returns:
            ResponseModel: A ResponseModel instance with the provided parameters.
        """
        return cls(pkg_id=pkg_id, req_id=req_id, status_code=0, data=data)

    @classmethod
    def err_msg(
        cls, pkg_id: int, req_id: Optional[UUID], data: dict
    ) -> "ResponseModel":
        """
        Create a ResponseModel instance with a status_code of -1, indicating an error response.

        Args:
            pkg_id (int): The package ID associated with the response.
            req_id (Optional[UUID]): The request ID associated with the response.
            data (dict): The data to be included in the response.

        Returns:
            ResponseModel: A ResponseModel instance with the provided parameters.
        """
        return cls(pkg_id=pkg_id, req_id=req_id, status_code=-1, data=data)
