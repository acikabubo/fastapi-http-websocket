from typing import Dict, Type

from sqlalchemy.ext.asyncio import AsyncSession

from app.contants import PkgID
from app.handlers.base_handler import BaseHandler

# Create a registry dictionary to map pkg_id to handler classes
handler_registry: Dict[int, Type[BaseHandler]] = {}


def register_handler(*pkg_ids: PkgID):
    """
    Decorator to register a handler class for one or more package IDs.

    This decorator is used to register a `BaseHandler` subclass to handle processing
    for the specified package IDs. The registered handler class can then be retrieved
    using the `get_handler` function.

    Args:
        *pkg_ids (List[int]): One or more package IDs to register the handler for.

    Returns:
        Callable[[Type[BaseHandler]], Type[BaseHandler]]: A decorator that registers
            the decorated class for the specified package IDs.
    """

    def decorator(cls_: Type[BaseHandler]):
        for pkg_id in pkg_ids:
            handler_registry[pkg_id] = cls_
        return cls_

    return decorator


# Factory function to get the handler instance
def get_handler(pkg_id: int, session: AsyncSession) -> BaseHandler:
    """
    Get the appropriate handler instance for the given package ID.

    Args:
        pkg_id (int): The package ID to get the handler for.
        session (AsyncSession): The SQLAlchemy session to use for the handler.

    Returns:
        BaseHandler: The handler instance for the given package ID.

    Raises:
        ValueError: If no handler is registered for the given package ID.
    """
    handler_class = handler_registry.get(pkg_id)

    if handler_class is None:
        raise ValueError(f"No handler found for pkg_id {pkg_id}")

    return handler_class(session)
