from typing import Dict, Type

from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.base_handler import BaseHandler
from app.handlers.submodule_a import SubmoduleAHandler

# Create a registry dictionary to map pkg_id to handler classes
handler_registry: Dict[int, Type[BaseHandler]] = {
    1: SubmoduleAHandler,
    # Add other handlers here, e.g.:
    # 2: SubmoduleBHandler,
    # 3: SubmoduleCHandler,
}


# Factory function to get the handler instance
def get_handler(pkg_id: int, session: AsyncSession) -> BaseHandler:
    handler_class = handler_registry.get(pkg_id)
    if handler_class:
        return handler_class(session)
    else:
        raise ValueError(f"No handler found for pkg_id {pkg_id}")
