"""
Base model for all database tables with async relationship support.

This module provides the BaseModel class that all SQLModel table models
should inherit from. It includes SQLAlchemy's AsyncAttrs mixin to enable
proper handling of lazy-loaded relationships in async contexts.
"""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlmodel import SQLModel


class BaseModel(SQLModel, AsyncAttrs):  # type: ignore[misc]
    """
    Base model for all database tables with async relationship support.

    This class combines SQLModel with SQLAlchemy's AsyncAttrs mixin to
    enable accessing lazy-loaded relationships via the awaitable_attrs
    accessor, preventing MissingGreenlet errors in async contexts.

    All table models in the application should inherit from this base class
    to ensure consistent async behavior across the codebase.

    Example:
        Basic model without relationships:
            class User(BaseModel, table=True):
                id: int | None = Field(default=None, primary_key=True)
                username: str
                email: str

        Model with relationships:
            class Author(BaseModel, table=True):
                id: int | None = Field(default=None, primary_key=True)
                name: str
                books: list["Book"] = Relationship(back_populates="author")

            class Book(BaseModel, table=True):
                id: int | None = Field(default=None, primary_key=True)
                title: str
                author_id: int = Field(foreign_key="author.id")
                author: Author = Relationship(back_populates="books")

    Usage:
        Preferred approach (eager loading for better performance):
            from sqlalchemy.orm import selectinload

            async with async_session() as session:
                stmt = select(Author).options(
                    selectinload(Author.books)
                )
                result = await session.execute(stmt)
                author = result.scalar_one()
                books = author.books  # Already loaded, no await needed

        Alternative approach (lazy loading when needed):
            async with async_session() as session:
                author = await session.get(Author, 1)
                # Access lazy-loaded relationship asynchronously
                books = await author.awaitable_attrs.books

    Note:
        - Eager loading (selectinload, joinedload) is preferred for
          better performance and fewer database queries
        - Use awaitable_attrs only for dynamic relationship access or
          when eager loading would load unnecessary data
        - AsyncAttrs has no performance penalty if relationships are
          not used, making it safe to use as a base for all models
    """

    pass
