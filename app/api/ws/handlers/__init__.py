import importlib
import pkgutil


def load_handlers():
    """
    Dynamically loads all ws handlers in the handlers package to
    trigger the registration of handlers via decorators.
    """
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        importlib.import_module(f"{__name__}.{module_name}")


# Load handlers at import time
load_handlers()
