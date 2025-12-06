from sqlmodel import Field, SQLModel


class Author(SQLModel, table=True):
    """
    SQLModel representing an author entity in the database.

    This is a clean data model without Active Record methods.
    Use AuthorRepository for all database operations.

    Attributes:
        id: Primary key identifier for the author
        name: Name of the author
    """

    __table_args__ = {"extend_existing": True}  # for pydoc

    id: int | None = Field(default=None, primary_key=True)
    name: str
