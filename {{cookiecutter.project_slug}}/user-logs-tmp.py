import asyncio
from contextvars import ContextVar
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

# Context variable to store the current user
current_user_var = ContextVar("current_user", default=None)


class EntityLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str
    entity_id: int
    action: str
    old_values: dict = Field(sa_column=Column(JSON))
    new_values: dict = Field(sa_column=Column(JSON))
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime)
    )
    logged_user_id: Optional[int] = Field(
        default=None
    )  # New field for logged user


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str


async def log_changes(
    async_session,
    entity_type: str,
    action: str,
    old_values: dict,
    new_values: dict,
):
    async with async_session() as session:
        current_user = current_user_var.get()
        entity_log = EntityLog(
            entity_type=entity_type,
            entity_id=new_values.get("id") or old_values.get("id"),
            action=action,
            old_values=old_values,
            new_values=new_values,
            logged_user_id=current_user.id if current_user else None,
        )
        session.add(entity_log)
        await session.commit()


def setup_logging(entity_class):
    @event.listens_for(entity_class, "after_insert")
    def log_insert(mapper, connection, target):
        new_values = {
            c.key: getattr(target, c.key) for c in mapper.column_attrs
        }
        asyncio.create_task(
            log_changes(
                async_session, entity_class.__name__, "create", {}, new_values
            )
        )

    @event.listens_for(entity_class, "after_update")
    def log_update(mapper, connection, target):
        state = target._sa_instance_state
        old_values = {}
        new_values = {}
        for attr in state.attrs:
            hist = attr.history
            if hist.has_changes():
                old_values[attr.key] = (
                    hist.deleted[0] if hist.deleted else None
                )
                new_values[attr.key] = hist.added[0] if hist.added else None
        asyncio.create_task(
            log_changes(
                async_session,
                entity_class.__name__,
                "update",
                old_values,
                new_values,
            )
        )

    @event.listens_for(entity_class, "after_delete")
    def log_delete(mapper, connection, target):
        old_values = {
            c.key: getattr(target, c.key) for c in mapper.column_attrs
        }
        asyncio.create_task(
            log_changes(
                async_session, entity_class.__name__, "delete", old_values, {}
            )
        )


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_async_engine("sqlite+aiosqlite:///database.db")
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

setup_logging(User)


# Simulating a login mechanism
class CurrentUser:
    def __init__(self, id, name):
        self.id = id
        self.name = name


def login_user(user):
    current_user_var.set(user)


def logout_user():
    current_user_var.set(None)


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Simulate logging in a user
    admin_user = CurrentUser(id=1, name="Admin")
    login_user(admin_user)

    async with async_session() as session:
        # # Create User
        # new_user = User(name="John Doe", email="john@example.com")
        # session.add(new_user)
        # await session.commit()

        # Update User
        user = await session.exec(
            select(User).where(User.email == "john@example.com")
        )
        user = user.one()
        user.email = "new-mail@example.com"
        await session.commit()

        # Simulate changing the logged-in user
        customer_user = CurrentUser(id=2, name="Customer")
        login_user(customer_user)

        # Delete User
        await session.delete(user)
        await session.commit()

    # Allow some time for async tasks to complete
    await asyncio.sleep(1)

    # Simulate logging out
    logout_user()

    await engine.dispose()


# Run the async main function
asyncio.run(main())
