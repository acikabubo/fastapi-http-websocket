from typing import Callable, Dict

from app.logging import logger

handler_registry: Dict[int, Callable] = {}


def register_handler(*pkg_ids: int):
    """
    Registers a handler function for the specified package IDs.

    The `register_handler` decorator can be used to register a handler function for one or more package IDs. The handler function will be stored in the `handler_registry` dictionary, which can be used to retrieve the handler later using the `get_handler` function.

    If a handler is already registered for any of the specified package IDs, a `ValueError` will be raised.

    Args:
        *pkg_ids (int): One or more package IDs to register the handler for.

    Returns:
        Callable: The original handler function, decorated with the registration logic.
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


def get_handler(pkg_id: int) -> Callable:
    """
    Retrieves the handler function registered for the specified package ID.

    If no handler has been registered for the given package ID, a `ValueError` is raised.

    Args:
        pkg_id (int): The package ID to retrieve the handler for.

    Returns:
        Callable: The handler function registered for the specified package ID.

    Raises:
        ValueError: If no handler has been registered for the given package ID.
    """
    if pkg_id not in handler_registry:
        raise ValueError(f"No handler found for pkg_id {pkg_id}")

    return handler_registry[pkg_id]
