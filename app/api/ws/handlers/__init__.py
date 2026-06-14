import importlib
import pkgutil
import sys


def load_handlers():  # type: ignore[no-untyped-def]
    """
    Dynamically loads all ws handlers in the handlers package to
    trigger the registration of handlers via decorators.

    Reloads already-cached modules so that decorators re-run after the
    handler registry has been cleared (e.g. on uvicorn hot-reload).
    """
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        full_name = f"{__name__}.{module_name}"
        if full_name in sys.modules:
            importlib.reload(sys.modules[full_name])
        else:
            importlib.import_module(full_name)
