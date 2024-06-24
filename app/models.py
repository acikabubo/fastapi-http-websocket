from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class BaseModel(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, index=True)


# class Association(BaseModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     author_id: Optional[int] = Field(default=None, foreign_key="author.id")
#     genre_id: Optional[int] = Field(default=None, foreign_key="genre.id")


class Author(BaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # books: List["Book"] = Relationship(back_populates="author")
    # genres: List["Genre"] = Relationship(
    #     back_populates="author", link_model=Association
    # )


# class Book(BaseModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     title: str
#     author_id: Optional[int] = Field(default=None, foreign_key="author.id")
#     author: Optional[Author] = Relationship(back_populates="books")


# class Genre(BaseModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     name: str
#     authors: List[Author] = Relationship(
#         back_populates="genres", link_model=Association
#     )


# Author.genres = Relationship(back_populates="authors", link_model=Association)
