from typing import Callable, Dict

from app.api.routers.ws.constants import PkgID
from app.core.logging import logger
from app.schemas.generic import HandlerCallableType

handler_registry: Dict[PkgID, HandlerCallableType] = {}


def register_handler(*pkg_ids: PkgID):
    """
    A decorator that registers a handler function for the specified package IDs.

    The `register_handler` decorator takes one or more package IDs as arguments and associates the decorated function with those IDs in the `handler_registry` dictionary. If a handler has already been registered for any of the specified package IDs, a `ValueError` is raised.

    The decorator logs a message for each package ID that a handler is registered for.

    Args:
        *pkg_ids (PkgID): One or more package IDs to register the handler function for.

    Returns:
        Callable: A decorator that wraps the original function and registers it in the `handler_registry`.

    Raises:
        ValueError: If a handler has already been registered for any of the specified package IDs.
    """

    def decorator(func: Callable):
        for pkg_id in pkg_ids:
            if pkg_id in handler_registry:
                raise ValueError(
                    f"Handler already registered for pkg_id {pkg_id}"
                )
            handler_registry[pkg_id] = func

            logger.info(
                f"Registered {func.__module__}.{func.__name__} for PkgID: {pkg_id}"
            )

        return func

    return decorator


def get_handler(pkg_id: PkgID) -> Callable:
    """
    Get the handler function registered for the specified package ID.

    Args:
        pkg_id (PkgID): The package ID to get the handler for.

    Returns:
        Callable: The handler function registered for the specified package ID.

    Raises:
        ValueError: If no handler has been registered for the specified package ID.
    """
    if pkg_id not in handler_registry:
        raise ValueError(f"No handler found for pkg_id {pkg_id}")

    return handler_registry[pkg_id]
